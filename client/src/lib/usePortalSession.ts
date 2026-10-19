"use client";

import { useCallback } from "react";

import type { Portal, RunStatus } from "@/lib/api";
import {
  attachRun,
  beginLaunch,
  failLaunch,
  patchRunStatus,
  resetScraperState,
  setSessionError,
  useSession,
} from "@/lib/sessions";

/**
 * A portal panel's view of its slot. The run, the launch error and the
 * launching flag all live in the session registry, so the panel renders the
 * same thing whether it has been mounted for an hour or for a millisecond.
 * Mounting reads; it never starts, stops or resets anything. Form state stays
 * local to the panel.
 */
export function usePortalSession(portal: Portal) {
  const session = useSession(portal);

  /** Launch a scrape and hand the run to the engine. No interval is created
   *  here: the panel is not what watches the run. */
  const launch = useCallback(
    async (start: () => Promise<{ run_id: string }>): Promise<string | null> => {
      beginLaunch(portal);
      try {
        const { run_id } = await start();
        // Registered before the first status arrives, so the panel switches to
        // the running view on the click rather than on the next engine tick.
        attachRun(portal, run_id);
        return run_id;
      } catch (e) {
        failLaunch(portal, (e as Error).message);
        return null;
      }
    },
    [portal],
  );

  const setError = useCallback(
    (message: string | null) => setSessionError(portal, message),
    [portal],
  );

  /** Apply a status this console just caused (pause/resume) without waiting. */
  const applyStatus = useCallback(
    (status: RunStatus["status"]) => patchRunStatus(portal, status),
    [portal],
  );

  /** The panel's Refresh button: back to a never-launched state. Does not touch
   *  the server — an in-flight run must be stopped by the caller first. */
  const reset = useCallback(() => resetScraperState(portal), [portal]);

  return {
    run: session?.run ?? null,
    error: session?.error ?? null,
    starting: session?.starting ?? false,
    // Whether there is anything for Refresh to clear.
    hasSession: !!session?.runId,
    launch,
    setError,
    applyStatus,
    reset,
  };
}
