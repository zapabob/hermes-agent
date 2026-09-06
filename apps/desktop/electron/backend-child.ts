/**
 * backend-child.ts
 *
 * Windows-aware teardown for the desktop's managed backend child process.
 *
 * On Windows, `ChildProcess.kill()` terminates through the process handle Node
 * retained when it spawned the child. That handle is the authority boundary:
 * never replace it with a PID-only `taskkill`, because a reused PID could
 * target a process this Desktop instance did not create. Descendants that keep
 * update files locked make the update fail closed at the release gate.
 *
 * On POSIX the backend IS spawned into its own session/process-group
 * (start_new_session=True), so `child.kill('SIGTERM')` would only reach the
 * backend and orphan its MCP grandchildren (the leak in #serve-orphans). We
 * signal the whole group via `process.kill(-pid, ...)` instead, falling back
 * to the direct child if the group send fails.
 *
 * Extracted into its own dependency-free module (no electron import) so the
 * tree-kill / group-kill branching can be asserted directly with a fake child
 * object and spy kill functions, instead of grepping main.ts source text for
 * the function body.
 */

export interface StopBackendChildDeps {
  /** Defaults to the real platform check; injectable for tests. */
  isWindows?: boolean
  /**
   * POSIX group-signal implementation. Real: process.kill(-pgid, signal).
   * Injectable so the negative-pid group send is asserted in tests without a
   * live process group. Defaults to process.kill.
   */
  killGroup?: (pgid: number, signal: string) => void
}

export interface StopBackendTreesForUpdateDeps {
  /** Clears and stops the desktop's pooled backends. */
  stopAllPoolBackends: () => void
}

export interface BackendProcessRoot {
  pid?: number | null
}

export interface KillableChild extends BackendProcessRoot {
  killed?: boolean
  kill: (signal: string) => void
}

/**
 * Stop a managed child process, choosing the right strategy for the platform.
 * No-ops silently if `child` is falsy, already killed, or the kill attempt
 * throws (the process may already be gone) -- mirrors the original inline
 * best-effort semantics in main.ts.
 */
export function stopBackendChild(child: KillableChild | null | undefined, deps: StopBackendChildDeps) {
  if (!child || child.killed) {
    return
  }

  const isWindows = deps.isWindows ?? process.platform === 'win32'
  const killGroup = deps.killGroup ?? ((pgid: number, signal: string) => process.kill(pgid, signal))

  try {
    if (isWindows) {
      child.kill('SIGTERM')
    } else if (Number.isInteger(child.pid)) {
      // POSIX: pgid == pid (start_new_session). Signal the whole group so MCP
      // grandchildren die too; fall back to the direct child on failure.
      try {
        killGroup(-(child.pid as number), 'SIGTERM')
      } catch {
        child.kill('SIGTERM')
      }
    } else {
      child.kill('SIGTERM')
    }
  } catch {
    // Already gone.
  }
}

/**
 * Stop every backend child for which this Desktop still retains a spawn
 * handle, then delegate pooled teardown to the same handle-bound routine.
 */
export function stopBackendTreesForUpdate(
  primary: BackendProcessRoot | null | undefined,
  deps: StopBackendTreesForUpdateDeps
): void {
  stopBackendChild(primary as KillableChild | null | undefined, { isWindows: true })

  deps.stopAllPoolBackends()
}
