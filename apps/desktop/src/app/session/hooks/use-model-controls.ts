import { type QueryClient } from '@tanstack/react-query'
import { useCallback, useRef } from 'react'

import type { ModelSelection } from '@/app/shell/model-menu-panel'
import { getGlobalModelInfo } from '@/hermes'
import { useI18n } from '@/i18n'
import { isBusySessionModelSwitch } from '@/lib/gateway-rpc'
import { manualPickRemoved, modelOptionsQueryKey } from '@/lib/model-options'
import { dismissNotification, notify, notifyError } from '@/store/notifications'
import { $activeGatewayProfile } from '@/store/profile'
import {
  $activeSessionId,
  $currentModel,
  $currentProvider,
  getComposerSelectionGeneration,
  getCurrentModelSource,
  markComposerSelectionManual,
  setCurrentModel,
  setCurrentModelSource,
  setCurrentProvider
} from '@/store/session'
import { sessionTileDelegate } from '@/store/session-states'
import type { ModelOptionsResponse } from '@/types/hermes'

interface ModelControlsOptions {
  cacheOwnerConnectionId?: string
  cacheProfile?: string
  queryClient: QueryClient
  requestGateway: <T = unknown>(method: string, params?: Record<string, unknown>) => Promise<T>
}

interface ModelSwitchGatewayResponse {
  confirm_message?: string
  confirm_required?: boolean
  deferred?: boolean
  provider?: string
  value?: string
  warning?: string
}

export function useModelControls({
  cacheOwnerConnectionId,
  cacheProfile,
  queryClient,
  requestGateway
}: ModelControlsOptions) {
  const { t } = useI18n()
  const copy = t.desktop
  const profileRefreshEpochRef = useRef(0)
  const selectionEpochByTargetRef = useRef(new Map<string, number>())

  // All callbacks here read reactive session state from the store (.get())
  // rather than capturing it as a prop. The actions bag in wiring.tsx mutates
  // in place to keep a stable identity, so memoized surfaces capture these
  // callbacks once and never re-evaluate — a captured prop would be stale
  // forever. The store read is always current.
  const updateModelOptionsCache = useCallback(
    (
      sessionId: null | string,
      provider: string,
      model: string,
      includeGlobal: boolean,
      profile = cacheProfile || $activeGatewayProfile.get(),
      ownerConnectionId = cacheOwnerConnectionId
    ) => {
      const patch = (prev: ModelOptionsResponse | undefined) => {
        // Selection state can update before the catalog query has resolved.
        // Keep that optimistic cache structurally complete; the composer
        // interprets a response without `providers` as an empty catalog.
        const providers = prev?.providers?.length
          ? prev.providers
          : provider && model
            ? [{ models: [model], name: provider, slug: provider }]
            : []

        return { ...prev, provider, model, providers }
      }

      queryClient.setQueryData<ModelOptionsResponse>(modelOptionsQueryKey(profile, sessionId, ownerConnectionId), patch)

      if (includeGlobal) {
        queryClient.setQueryData<ModelOptionsResponse>(modelOptionsQueryKey(profile, null, ownerConnectionId), patch)
      }
    },
    [cacheOwnerConnectionId, cacheProfile, queryClient]
  )

  // Settings → Model writes the profile default, which the backend applies to
  // new sessions only. Keep a live session's renderer state and session-scoped
  // model-options cache authoritative instead of briefly painting the saved
  // default as if the active agent had switched. Marking the composer as
  // default-derived still lets the next fresh draft reseed from profile config.
  const applySavedMainModel = useCallback(
    (provider: string, model: string) => {
      const liveSessionId = $activeSessionId.get()

      setCurrentModelSource('default')

      if (!liveSessionId) {
        setCurrentProvider(provider)
        setCurrentModel(model)
      }

      // A null session id is the profile-global model-options key. Never patch
      // the live session key here: only config.set --session may change it.
      updateModelOptionsCache(null, provider, model, false)
    },
    [updateModelOptionsCache]
  )

  // Seed the composer's model state from the profile default. `force` reseeds
  // for a profile swap (the new profile has its own default); otherwise this
  // only fills an EMPTY selection so a user's pick (plain UI state in
  // $currentModel) survives the lifecycle refreshes that fire on boot / fresh
  // draft / session events. A live session owns the footer, so skip entirely.
  const refreshCurrentModel = useCallback(
    async (force = false) => {
      // A forced profile swap opens a new intent epoch; an older in-flight
      // response for a previous profile must stand down when it resolves.
      if (force) {
        profileRefreshEpochRef.current += 1
        selectionEpochByTargetRef.current.clear()
      }

      const profileRefreshEpoch = profileRefreshEpochRef.current
      const profile = cacheProfile || $activeGatewayProfile.get()

      try {
        if ($activeSessionId.get()) {
          return
        }

        // A manual pick stays sticky UNLESS it was removed from the catalog (its
        // model no longer exists on the provider), in which case keeping it would
        // 404 every new chat — fall through to reseed from the profile default.
        // Reads the model-options cache the composer already populated; an
        // unknown/not-yet-loaded catalog conservatively preserves the pick.
        const keepManualPick = () => {
          if (force || !$currentModel.get() || getCurrentModelSource() !== 'manual') {
            return false
          }

          const options = queryClient.getQueryData<ModelOptionsResponse>(
            modelOptionsQueryKey(profile, null, cacheOwnerConnectionId)
          )

          return !manualPickRemoved(options?.providers, $currentProvider.get(), $currentModel.get())
        }

        if (keepManualPick()) {
          return
        }

        // Snapshot the selection generation before awaiting so a picker click
        // that lands while getGlobalModelInfo is in flight wins over this older
        // default — value comparisons alone miss re-selecting the same row.
        const selectionGeneration = getComposerSelectionGeneration()
        const result = await getGlobalModelInfo(profile)

        if (
          profileRefreshEpochRef.current !== profileRefreshEpoch ||
          $activeSessionId.get() ||
          getComposerSelectionGeneration() !== selectionGeneration ||
          keepManualPick()
        ) {
          return
        }

        if (typeof result.model === 'string') {
          setCurrentModel(result.model)
        }

        if (typeof result.provider === 'string') {
          setCurrentProvider(result.provider)
        }

        if (typeof result.model === 'string' || typeof result.provider === 'string') {
          setCurrentModelSource('default')
        }
      } catch {
        // The delayed session.info event still updates this once the agent is ready.
      }
    },
    [cacheOwnerConnectionId, cacheProfile, queryClient]
  )

  // Returns whether the switch succeeded so callers can await it before applying
  // follow-up changes. The composer model is plain UI state: with no live
  // session it's just stored (and shipped on the next session.create); with one
  // it's scoped to that session via config.set. It NEVER writes the profile
  // default — that lives in Settings → Model — so picking a model here can't
  // silently mutate global config.
  //
  // `selection.sessionId` targets a specific surface (tile). When omitted, the
  // primary `$activeSessionId` is used (overlay / legacy callers). A tile
  // switch must not touch the primary globals — and must not be blocked by a
  // busy primary turn.
  const selectModel = useCallback(
    async (selection: ModelSelection): Promise<boolean> => {
      const primaryRuntimeId = $activeSessionId.get()
      const liveSessionId = 'sessionId' in selection ? (selection.sessionId ?? null) : primaryRuntimeId
      const touchesPrimary = !liveSessionId || liveSessionId === primaryRuntimeId
      const liveGatewayProfile = cacheProfile || $activeGatewayProfile.get()
      const selectionTarget = `${cacheOwnerConnectionId ?? '<ambient>'}\u0000${liveGatewayProfile}\u0000${liveSessionId ?? '<new-session>'}`
      const selectionEpoch = (selectionEpochByTargetRef.current.get(selectionTarget) ?? 0) + 1
      selectionEpochByTargetRef.current.set(selectionTarget, selectionEpoch)

      const selectionIsCurrent = () =>
        selectionEpochByTargetRef.current.get(selectionTarget) === selectionEpoch &&
        (cacheProfile !== undefined || $activeGatewayProfile.get() === liveGatewayProfile) &&
        (!touchesPrimary || $activeSessionId.get() === primaryRuntimeId)

      const commitSelection = (applied: ModelSelection = selection) => {
        if (!selectionIsCurrent()) {
          return false
        }

        if (liveSessionId) {
          sessionTileDelegate()?.updateSession(liveSessionId, state => ({
            ...state,
            model: applied.model,
            provider: applied.provider
          }))
        }

        if (touchesPrimary) {
          setCurrentModel(applied.model)
          setCurrentProvider(applied.provider)
          markComposerSelectionManual()
        }

        updateModelOptionsCache(
          liveSessionId,
          applied.provider,
          applied.model,
          touchesPrimary && !liveSessionId,
          liveGatewayProfile
        )

        return true
      }

      const commitAcknowledged = (result: ModelSwitchGatewayResponse | undefined) => {
        const acknowledgedSelection: ModelSelection = {
          ...selection,
          model: result?.value || selection.model,
          provider: result?.provider || selection.provider
        }

        if (!commitSelection(acknowledgedSelection)) {
          return false
        }

        if (cacheOwnerConnectionId && !result?.deferred) {
          void queryClient.invalidateQueries({
            queryKey: modelOptionsQueryKey(liveGatewayProfile, liveSessionId, cacheOwnerConnectionId)
          })
        }

        return true
      }

      // No live session yet: the pick is pure UI state. session.create reads
      // $currentModel/$currentProvider and applies it as that session's override.
      if (!liveSessionId) {
        return commitSelection()
      }

      try {
        // Model switches made from a session tab/tile/composer are strictly session-scoped
        // (--session) to prevent cross-tab and cross-session model routing contamination.
        // The global profile default is configured explicitly in Settings → Model.
        const scope = '--session'

        const params: Record<string, unknown> = {
          session_id: liveSessionId,
          key: 'model',
          value: `${selection.model} --provider ${selection.provider} ${scope}`
        }

        const result = await requestGateway<ModelSwitchGatewayResponse>('config.set', params)

        if (result?.confirm_required) {
          // A guard response is not an acknowledgement. Keep the visible
          // selection unchanged and require an explicit confirmation before
          // resubmitting the same request. The epoch check prevents a stale
          // warning from clobbering a later picker choice.
          let notificationId = ''

          const confirm = () => {
            dismissNotification(notificationId)

            if (!selectionIsCurrent()) {
              return
            }

            void requestGateway<ModelSwitchGatewayResponse>('config.set', {
              ...params,
              confirm_expensive_model: true
            })
              .then(confirmed => {
                if (confirmed?.confirm_required) {
                  throw new Error(confirmed.confirm_message || confirmed.warning || copy.modelSwitchFailed)
                }

                commitAcknowledged(confirmed)
              })
              .catch(error => {
                if (selectionIsCurrent()) {
                  notifyError(error, copy.modelSwitchFailed)
                }
              })
          }

          notificationId = notify({
            action: { label: t.common.confirm, onClick: confirm },
            kind: 'warning',
            message: result.confirm_message || result.warning || copy.modelSwitchFailed,
            title: t.common.confirm
          })

          return false
        }

        // Commit only after the gateway either switched the live runtime or
        // accepted a guarded, turn-boundary-safe deferred switch.
        return commitAcknowledged(result)
      } catch (err) {
        // An OLDER gateway refuses a mid-turn switch outright (4009) instead of
        // deferring it. Don't punish the user for a backend they haven't
        // updated: keep the pick painted as the composer's selection, which is
        // what the NEXT turn runs anyway. Current gateways never take this
        // path — they answer `deferred`.
        if (isBusySessionModelSwitch(err)) {
          return commitSelection()
        }

        if (selectionIsCurrent()) {
          notifyError(err, copy.modelSwitchFailed)
        }

        return false
      }
    },
    [
      cacheOwnerConnectionId,
      cacheProfile,
      copy.modelSwitchFailed,
      queryClient,
      requestGateway,
      t.common.confirm,
      updateModelOptionsCache
    ]
  )

  return { applySavedMainModel, refreshCurrentModel, selectModel }
}
