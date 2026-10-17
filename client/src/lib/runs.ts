import { listRuns, type Portal, type RunStatus } from "@/lib/api";

export interface RunsState {
  runs: RunStatus[] | null;
  error: string | null;
  loading: boolean;
}

export const RUNS_LOADING: RunsState = { runs: null, error: null, loading: true };

export async function fetchRunsState(portal: Portal, what: string): Promise<RunsState> {
  try {
    const data = await listRuns(portal);
    return { runs: sortByNewest(data.runs ?? []), error: null, loading: false };
  } catch (e) {
    return {
      runs: [],
      error: `Could not load ${what} — is the API running? (${(e as Error).message})`,
      loading: false,
    };
  }
}

/** `2026-07-17T00:29:11` → `17 Jul 2026, 00:29`. */
export function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Wall-clock length of a run, or "—" while it is still going. */
export function formatDuration(run: RunStatus): string {
  if (!run.started_at || !run.finished_at) return "—";
  const ms = new Date(run.finished_at).getTime() - new Date(run.started_at).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

/** Newest first — the backend does not guarantee ordering. */
function sortByNewest(runs: RunStatus[]): RunStatus[] {
  return [...runs].sort(
    (a, b) => new Date(b.started_at ?? 0).getTime() - new Date(a.started_at ?? 0).getTime(),
  );
}

/** Short human label for what a run was searching for. */
export function runTarget(run: RunStatus): string {
  return run.search || "All active tenders";
}

/** A completed run, or a stopped one that kept rows, has a workbook to download. */
export function runDownloadable(run: RunStatus): boolean {
  return run.status === "completed" || runPartial(run);
}

export function runPartial(run: RunStatus): boolean {
  return run.status === "stopped" && Boolean(run.partial_results);
}
