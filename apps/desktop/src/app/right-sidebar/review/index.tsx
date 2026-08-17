import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { FileDiffPanel } from '@/components/chat/diff-lines'
import { DiffSkeleton, TreeSkeleton } from '@/components/chat/skeletons'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { DiffCount } from '@/components/ui/diff-count'
import { SegmentedControl } from '@/components/ui/segmented-control'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tip } from '@/components/ui/tooltip'
import { useDelayedTrue } from '@/hooks/use-delayed-true'
import { useI18n } from '@/i18n'
import { displayPath } from '@/lib/display-path'
import { cn } from '@/lib/utils'
import { desktopGit } from '@/lib/desktop-git'
import { $panesFlipped } from '@/store/layout'
import { notifyError } from '@/store/notifications'
import {
  $currentCwd,
  $reviewDiff,
  $reviewDiffLoading,
  $reviewFiles,
  $reviewHistoryLoading,
  $reviewIsRepo,
  $reviewLoading,
  $reviewRevertTarget,
  $reviewScopeCwd,
  $reviewSelectedPath,
  $reviewTreeMode,
  $reviewView,
  cancelRevert,
  clearReviewSelection,
  closeReview,
  confirmRevert,
  openReview,
  refreshReview,
  refreshReviewHistory,
  requestRevert,
  setReviewView,
  stageReviewFile,
  toggleReviewTreeMode,
  unstageReviewFile
} from '@/store/review'
import { $scmBranchesLoading, $scmStashesLoading, $scmTagsLoading, refreshScmRefs } from '@/store/scm-refs'

import { SidebarPanelLabel } from '../../shell/sidebar-label'
import { PaneEmptyState, RightSidebarSectionHeader } from '../index'

import { ReviewFileTree } from './file-tree'
import { ReviewHistory } from './history'
import { ReviewScmRail } from './scm-rail'
import { ReviewShipBar } from './ship-bar'

// Compact header/diff action buttons — micro hit targets packed tight, matching
// the rest of the app's icon-action rows.
const ACTION_BTN = 'size-5'

export function ReviewPane() {
  const { t } = useI18n()
  const c = t.statusStack.coding
  const panesFlipped = useStore($panesFlipped)
  const files = useStore($reviewFiles)
  const loading = useStore($reviewLoading)
  const historyLoading = useStore($reviewHistoryLoading)
  const isRepo = useStore($reviewIsRepo)
  const selectedPath = useStore($reviewSelectedPath)
  const diff = useStore($reviewDiff)
  const diffLoading = useStore($reviewDiffLoading)
  const revertTarget = useStore($reviewRevertTarget)
  const treeMode = useStore($reviewTreeMode)
  const view = useStore($reviewView)
  const branchesLoading = useStore($scmBranchesLoading)
  const tagsLoading = useStore($scmTagsLoading)
  const stashesLoading = useStore($scmStashesLoading)
  const scmLoading = branchesLoading || tagsLoading || stashesLoading
  const currentCwd = useStore($currentCwd)
  const scopeCwd = useStore($reviewScopeCwd)

  // Worktree switcher
  const [worktrees, setWorktrees] = useState<Array<{ path: string; branch: string }>>([])
  const [worktreesLoading, setWorktreesLoading] = useState(false)

  useEffect(() => {
    const cwd = scopeCwd?.trim() || currentCwd?.trim()
    if (!cwd || !desktopGit()?.worktreeList) {
      setWorktrees([])
      return
    }
    setWorktreesLoading(true)
    desktopGit()!.worktreeList(cwd).then(wts => {
      setWorktrees(wts.map(wt => ({ path: wt.path, branch: wt.branch })))
      setWorktreesLoading(false)
    }).catch(() => {
      setWorktrees([])
      setWorktreesLoading(false)
    })
  }, [scopeCwd, currentCwd])

  const selectedFile = files.find(file => file.path === selectedPath)
  const hasFiles = files.length > 0
  // `{ path: null }` → revert all; `{ path: '…' }` → revert one file.
  const revertingAll = revertTarget?.path == null
  // Delay the skeletons so fast loads (most project switches) just blank → content
  // instead of flashing a jarring loading state.
  const showTreeSkeleton = useDelayedTrue(loading && !hasFiles)
  const showDiffSkeleton = useDelayedTrue(diffLoading)

  // Repo switcher options
  const repoOptions = worktrees.map(wt => ({
    value: wt.path,
    label: `${wt.branch} (${wt.path.split(/[\\/]+/).filter(Boolean).pop()})`
  }))
  const isScoped = Boolean(scopeCwd)
  const currentRepoLabel = isScoped
    ? repoOptions.find(o => o.value === scopeCwd)?.label || scopeCwd
    : currentCwd?.split(/[\\/]+/).filter(Boolean).pop() || 'Session'

  return (
    <aside
      aria-label={c.review}
      className={cn(
        'before:pointer-events-none relative flex h-full w-full min-w-0 flex-col overflow-hidden border-(--ui-stroke-secondary) bg-(--ui-sidebar-surface-background) pt-(--titlebar-height) text-(--ui-text-tertiary)',
        panesFlipped
          ? 'border-r shadow-[inset_-0.0625rem_0_0_color-mix(in_srgb,white_18%,transparent)]'
          : 'border-l shadow-[inset_0.0625rem_0_0_color-mix(in_srgb,white_18%,transparent)]'
      )}
    >
      {(loading || historyLoading || isRepo || view === 'scm') && (
        <RightSidebarSectionHeader data-suppress-pane-reveal-side="">
          <div className="flex min-w-0 flex-1">
            {/* Pure self-naming label — redundant under a zone tab that already
                says "review", so the zone header hides it (styles.css). */}
            <SidebarPanelLabel data-pane-self-label="">{c.review}</SidebarPanelLabel>
          </div>
          <SegmentedControl
            className="mr-1"
            onChange={setReviewView}
            options={[
              { id: 'changes', label: c.changes },
              { id: 'history', label: c.history },
              { id: 'scm', label: c.scm }
            ]}
            value={view}
          />
          <div className="ml-2 mr-1 flex min-w-0 flex-1">
            <Tip label="Switch repository / worktree">
              <Select value={isScoped ? scopeCwd || '' : currentCwd || ''} onValueChange={path => path ? openReview(path) : openReview(null)}>
                <SelectTrigger className="w-full min-w-[160px] max-w-[280px]">
                  <SelectValue placeholder={currentRepoLabel} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">
                    <span className="flex items-center gap-2">
                      <Codicon name="sync" size="0.8rem" className="text-(--ui-text-tertiary)" />
                      Session: {currentCwd?.split(/[\\/]+/).filter(Boolean).pop() || 'default'}
                    </span>
                  </SelectItem>
                  {repoOptions.map(option => (
                    <SelectItem key={option.value} value={option.value}>
                      <span className="flex items-center gap-2">
                        <Codicon name="branch" size="0.8rem" className="text-(--ui-text-tertiary)" />
                        {option.label}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Tip>
          </div>
          {view === 'changes' && (
            <>
              <Tip label={treeMode === 'tree' ? c.viewAsList : c.viewAsTree}>
                <Button
                  aria-label={treeMode === 'tree' ? c.viewAsList : c.viewAsTree}
                  className={ACTION_BTN}
                  disabled={!hasFiles}
                  onClick={toggleReviewTreeMode}
                  size="icon-xs"
                  variant="ghost"
                >
                  <Codicon name={treeMode === 'tree' ? 'list-flat' : 'list-tree'} size="0.8125rem" />
                </Button>
              </Tip>
              <Tip label={c.stageAll}>
                <Button
                  aria-label={c.stageAll}
                  className={ACTION_BTN}
                  disabled={!hasFiles}
                  onClick={() => void stageReviewFile(null).catch(err => notifyError(err, c.stageAll))}
                  size="icon-xs"
                  variant="ghost"
                >
                  <Codicon name="add" size="0.8125rem" />
                </Button>
              </Tip>
              <Tip label={c.revertAll}>
                <Button
                  aria-label={c.revertAll}
                  className={ACTION_BTN}
                  disabled={!hasFiles}
                  onClick={() => requestRevert(null)}
                  size="icon-xs"
                  variant="ghost"
                >
                  <Codicon name="discard" size="0.8125rem" />
                </Button>
              </Tip>
              <Tip label={t.rightSidebar.refreshTree}>
                <Button
                  aria-label={t.rightSidebar.refreshTree}
                  className={ACTION_BTN}
                  onClick={() => void refreshReview()}
                  size="icon-xs"
                  variant="ghost"
                >
                  <Codicon name="refresh" size="0.8125rem" spinning={loading} />
                </Button>
              </Tip>
            </>
          )}
          {view === 'history' && (
            <Tip label={t.rightSidebar.refreshTree}>
              <Button
                aria-label={t.rightSidebar.refreshTree}
                className={ACTION_BTN}
                onClick={() => void refreshReviewHistory()}
                size="icon-xs"
                variant="ghost"
              >
                <Codicon name="refresh" size="0.8125rem" spinning={historyLoading} />
              </Button>
            </Tip>
          )}
          {view === 'scm' && (
            <Tip label={t.rightSidebar.refreshTree}>
              <Button
                aria-label={t.rightSidebar.refreshTree}
                className={ACTION_BTN}
                onClick={() => void refreshScmRefs()}
                size="icon-xs"
                variant="ghost"
              >
                <Codicon name="refresh" size="0.8125rem" spinning={scmLoading} />
              </Button>
            </Tip>
          )}
          <Button aria-label={c.close} className={ACTION_BTN} onClick={closeReview} size="icon-xs" variant="ghost">
            <Codicon name="close" size="0.8125rem" />
          </Button>
        </RightSidebarSectionHeader>
      )}

      {view === 'history' ? (
        <ReviewHistory />
      ) : view === 'scm' ? (
        <ReviewScmRail />
      ) : loading || isRepo ? (
        hasFiles ? (
          <ReviewFileTree />
        ) : showTreeSkeleton ? (
          <TreeSkeleton />
        ) : loading ? (
          <div className="min-h-0 flex-1" />
        ) : (
          <PaneEmptyState label={t.rightSidebar.noDiffs} />
        )
      ) : (
        // No repo at all → same terse empty state, just without the chrome.
        <PaneEmptyState label={t.rightSidebar.noDiffs} />
      )}

      {/* Selected file's diff — reuses the shiki-highlighted FileDiffPanel. */}
      {view === 'changes' && selectedFile && (
        <div className="flex max-h-[55%] shrink-0 flex-col border-t border-(--ui-stroke-secondary)">
          <div className="flex items-center gap-1 px-2.5 py-1.5" data-suppress-pane-reveal-side="">
            <span
              className="min-w-0 flex-1 truncate font-mono text-[0.66rem] text-(--ui-text-secondary)"
              title={displayPath(selectedFile.path)}
            >
              {displayPath(selectedFile.path)}
            </span>
            <DiffCount added={selectedFile.added} className="text-[0.64rem] leading-4" removed={selectedFile.removed} />
            <Tip label={selectedFile.staged ? c.unstage : c.stage}>
              <Button
                aria-label={selectedFile.staged ? c.unstage : c.stage}
                className={ACTION_BTN}
                onClick={() =>
                  void (
                    selectedFile.staged ? unstageReviewFile(selectedFile.path) : stageReviewFile(selectedFile.path)
                  ).catch(err => notifyError(err, c.stage))
                }
                size="icon-xs"
                variant="ghost"
              >
                <Codicon name={selectedFile.staged ? 'remove' : 'add'} size="0.8rem" />
              </Button>
            </Tip>
            <Button
              aria-label={c.close}
              className={ACTION_BTN}
              onClick={clearReviewSelection}
              size="icon-xs"
              variant="ghost"
            >
              <Codicon name="close" size="0.8rem" />
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-1 pb-1">
            {diffLoading ? (
              showDiffSkeleton ? (
                <DiffSkeleton />
              ) : null
            ) : diff ? (
              <FileDiffPanel className="mx-0 mb-0 h-full max-h-none" diff={diff} path={selectedFile.path} virtualized />
            ) : (
              <div className="py-6 text-center text-[0.66rem] text-muted-foreground/60">{c.noDiff}</div>
            )}
          </div>
        </div>
      )}

      {view === 'changes' && <ReviewShipBar />}

      <Dialog onOpenChange={open => !open && cancelRevert()} open={revertTarget !== undefined}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{revertingAll ? c.revertAll : c.revert}</DialogTitle>
            <DialogDescription>
              {revertingAll ? c.revertAllConfirm : c.revertConfirm}
              {!revertingAll && revertTarget?.path && (
                <span
                  className="mt-2 block truncate font-mono text-[0.7rem] text-(--ui-text-secondary)"
                  title={displayPath(revertTarget.path)}
                >
                  {displayPath(revertTarget.path)}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={cancelRevert} variant="ghost">
              {t.common.cancel}
            </Button>
            <Button onClick={() => void confirmRevert().catch(err => notifyError(err, c.revert))} variant="destructive">
              {revertingAll ? c.revertAll : c.revert}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
