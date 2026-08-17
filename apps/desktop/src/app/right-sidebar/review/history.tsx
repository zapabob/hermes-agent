import { useStore } from '@nanostores/react'

import { FileDiffPanel } from '@/components/chat/diff-lines'
import { DiffSkeleton, TreeSkeleton } from '@/components/chat/skeletons'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useDelayedTrue } from '@/hooks/use-delayed-true'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import {
  $reviewHistory,
  $reviewHistoryDiff,
  $reviewHistoryDiffLoading,
  $reviewHistoryLoading,
  $reviewRefFilter,
  $reviewSelectedCommit,
  clearReviewCommitSelection,
  selectReviewCommit,
  setReviewRefFilter
} from '@/store/review'
import { $scmBranches, $scmTags } from '@/store/scm-refs'

import { PaneEmptyState } from '../index'

import { buildCommitGraph } from './history-graph'

const ACTION_BTN = 'size-5'

function formatCommitTime(value: string): string {
  const timestamp = Date.parse(value)

  if (Number.isNaN(timestamp)) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(timestamp)
}

/** Read-only commit history. Diff content is requested only for the selected
 * commit, so opening projects with a long history has a fixed, small cost. */
export function ReviewHistory() {
  const { t } = useI18n()
  const c = t.statusStack.coding
  const commits = useStore($reviewHistory)
  const loading = useStore($reviewHistoryLoading)
  const selectedSha = useStore($reviewSelectedCommit)
  const diff = useStore($reviewHistoryDiff)
  const diffLoading = useStore($reviewHistoryDiffLoading)
  const scmBranches = useStore($scmBranches)
  const scmTags = useStore($scmTags)
  const selectedCommit = commits.find(commit => commit.sha === selectedSha)
  const rows = buildCommitGraph(commits)
  const maxLane = rows.reduce((m, r) => Math.max(m, r.lane), 0)
  const gutterWidth = 8 + maxLane * 12
  const refFilter = useStore($reviewRefFilter)
  const showListSkeleton = useDelayedTrue(loading && commits.length === 0)
  const showDiffSkeleton = useDelayedTrue(diffLoading)
  const remoteNames = Array.from(new Set(scmBranches.filter(b => b.isRemote).map(b => b.name.split('/')[0])))
  const filterOptions = ['all', 'local', ...remoteNames]

  return (
    <>
      <div aria-label={c.commitHistory} className="min-h-0 flex-1 overflow-auto" role="region">
        {commits.length > 0 ? (
          <div className="py-1">
            <div className="px-2.5 pb-2">
              <Select onValueChange={setReviewRefFilter} value={refFilter}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Ref filter" />
                </SelectTrigger>
                <SelectContent>
                  {filterOptions.map(option => (
                    <SelectItem key={option} value={option}>
                      {option === 'all' ? 'All' : option === 'local' ? 'Local' : option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {commits.map(commit => {
              const selected = commit.sha === selectedSha

              const matchingBranches =
                refFilter === 'all'
                  ? scmBranches.filter(b => b.sha === commit.sha).map(b => b.name)
                  : refFilter === 'local'
                    ? scmBranches.filter(b => !b.isRemote && b.sha === commit.sha).map(b => b.name)
                    : remoteNames.includes(refFilter)
                      ? scmBranches
                          .filter(b => b.sha === commit.sha && b.name.startsWith(refFilter + '/'))
                          .map(b => b.name)
                      : []

              const matchingTags = scmTags.filter(t => t.sha === commit.sha).map(t => t.name)

              return (
                <button
                  aria-current={selected ? 'true' : undefined}
                  className={cn(
                    'flex w-full flex-col gap-0.5 border-l-2 px-2.5 py-2 text-left transition-colors',
                    selected
                      ? 'border-(--ui-accent) bg-(--ui-bg-tertiary)'
                      : 'border-transparent hover:bg-(--ui-bg-tertiary)/70'
                  )}
                  key={commit.sha}
                  onClick={() => void selectReviewCommit(commit)}
                  type="button"
                >
                  <span className="truncate text-[0.72rem] font-medium text-(--ui-text-primary)" title={commit.subject}>
                    {commit.subject || commit.shortSha}
                  </span>
                  <span className="flex min-w-0 items-center gap-1.5 text-[0.62rem] text-(--ui-text-tertiary)">
                    <span className="shrink-0 font-mono text-(--ui-text-secondary)">{commit.shortSha}</span>
                    {commit.author && <span className="truncate">{commit.author}</span>}
                    <time className="ml-auto shrink-0" dateTime={commit.authoredAt}>
                      {formatCommitTime(commit.authoredAt)}
                    </time>
                  </span>
                  {/* ref markers: branch pills (accent) and tag pills (neutral) */}
                  {matchingBranches.length > 0 ||
                    (matchingTags.length > 0 && (
                      <span className="flex min-w-0 items-center gap-1 pt-1 text-[0.55rem]">
                        {matchingBranches.map(name => (
                          <span
                            className="shrink-0 rounded-full border border-(--ui-accent)/40 px-1 py-1 text-[0.55rem] leading-none text-(--ui-accent)"
                            key={name}
                          >
                            {name}
                          </span>
                        ))}
                        {matchingTags.length > 0 && (
                          <span className="shrink-0 rounded-full border border-(--ui-stroke-secondary) px-1 py-1 text-[0.55rem] leading-none text-(--ui-text-secondary)">
                            {matchingTags.join(' ')}
                          </span>
                        )}
                      </span>
                    ))}
                </button>
              )
            })}
          </div>
        ) : showListSkeleton ? (
          <TreeSkeleton />
        ) : loading ? (
          <div className="min-h-0 flex-1" />
        ) : (
          <PaneEmptyState label={c.noHistory} />
        )}
      </div>

      {selectedCommit && (
        <div className="flex max-h-[55%] shrink-0 flex-col border-t border-(--ui-stroke-secondary)">
          <div className="flex items-center gap-1 px-2.5 py-1.5">
            <Codicon className="text-(--ui-text-secondary)" name="git-commit" size="0.75rem" />
            <span
              className="min-w-0 flex-1 truncate text-[0.68rem] text-(--ui-text-secondary)"
              title={selectedCommit.subject}
            >
              {selectedCommit.subject || selectedCommit.shortSha}
            </span>
            <span className="font-mono text-[0.62rem] text-(--ui-text-tertiary)">{selectedCommit.shortSha}</span>
            <Button
              aria-label={c.close}
              className={ACTION_BTN}
              onClick={clearReviewCommitSelection}
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
              <FileDiffPanel
                className="mx-0 mb-0 h-full max-h-none"
                diff={diff}
                path={`${selectedCommit.shortSha}.diff`}
                virtualized
              />
            ) : (
              <div className="py-6 text-center text-[0.66rem] text-muted-foreground/60">{c.noDiff}</div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
