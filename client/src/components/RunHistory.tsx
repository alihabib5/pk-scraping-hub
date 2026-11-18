"use client";

import { useEffect, useState } from "react";

import PpraResults from "@/components/PpraResults";
import PunjabResults from "@/components/PunjabResults";
import RunStatusPanel from "@/components/RunStatus";
import { Button, DataTable, EmptyState, ErrorBanner, IconButton, LinkButton, RunBadge, Spinner } from "@/components/ui";
import { runDownloadUrl, type RunStatus } from "@/lib/api";
import { fetchRunsState, formatDuration, formatTimestamp, runDownloadable, runTarget, RUNS_LOADING, type RunsState } from "@/lib/runs";
import { runSerial, type PortalMeta } from "@/lib/portals";

/**
 * Every run the backend holds for this portal (`GET /{portal}/scrape/runs`).
 */
export default function RunHistory({ meta }: { meta: PortalMeta }) {
  const [{ runs, error, loading }, setState] = useState<RunsState>(RUNS_LOADING);
  const [selected, setSelected] = useState<RunStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchRunsState(meta.key, "run history").then((next) => {
      if (!cancelled) setState(next);
    });
    return () => {
      cancelled = true;
    };
  }, [meta.key]);

  const refresh = () => {
    setState((s) => ({ ...s, loading: true }));
    fetchRunsState(meta.key, "run history").then(setState);
  };

  if (selected) {
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <IconButton label="Back to run history" variant="secondary" onClick={() => setSelected(null)}>
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
              <path d="M10 3.5L5.5 8l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </IconButton>
          <div className="min-w-0">
            <h1 className="font-display text-xl text-ink-950">Run detail</h1>
            <p className="truncate text-xs text-ink-600">Opened from the {meta.label} register</p>
          </div>
        </div>
        <RunStatusPanel run={selected} />
        {selected.scraper === "punjab" ? (
          <PunjabResults runId={selected.run_id} />
        ) : (
          <PpraResults runId={selected.run_id} />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink-950">Run history</h1>
          <p className="mt-1 text-sm text-ink-600">
            Every {meta.label} run currently held by the server. Select a row to inspect it.
          </p>
        </div>
        <Button
          size="sm"
          onClick={refresh}
          loading={loading}
          icon={
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
              <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2v3h-3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          }
        >
          Refresh
        </Button>
      </div>

      {error && <ErrorBanner message={error} />}

      {runs === null && loading && (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-ink-200 bg-sheet py-14 text-sm text-ink-600">
          <Spinner />
          Loading run history…
        </div>
      )}

      {runs !== null && runs.length === 0 && !error && (
        <EmptyState
          icon={
            <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
              <circle cx="10" cy="10" r="7" />
              <path d="M10 6v4l2.5 2" strokeLinecap="round" />
            </svg>
          }
          title="No runs yet"
          description={`Once you start a ${meta.label} scrape from the Console, every run will be listed here.`}
        />
      )}

      {runs !== null && runs.length > 0 && (
        <DataTable
          caption={`${runs.length} ${runs.length === 1 ? "run" : "runs"}`}
          headers={[
            { label: "Serial" },
            { label: "Status" },
            { label: "Started" },
            { label: "Duration" },
            { label: "Searched for" },
            { label: "Bids", className: "text-right" },
            { label: "" },
          ]}
        >
          {runs.map((run) => (
            <tr
              key={run.run_id}
              onClick={() => setSelected(run)}
              className="cursor-pointer transition hover:bg-intaglio-50"
            >
              <td className="whitespace-nowrap px-4 py-2.5">
                {/* The serial is the run's name. The row is clickable for the
                    mouse; this button is the same action for the keyboard and
                    for screen readers. */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelected(run);
                  }}
                  className="rounded font-mono text-[13px] font-bold text-ink-950 underline decoration-ink-300 underline-offset-4 hover:decoration-intaglio-800"
                >
                  {runSerial(run.scraper, run.run_id)}
                </button>
              </td>
              <td className="px-4 py-2.5">
                <RunBadge status={run.status} partial={run.partial_results} />
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-ink-700">
                {formatTimestamp(run.started_at)}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-ink-700">{formatDuration(run)}</td>
              <td className="max-w-xs truncate px-4 py-2.5 text-ink-800" title={runTarget(run)}>
                {runTarget(run)}
              </td>
              <td className="px-4 py-2.5 text-right font-mono text-ink-900">{run.bids_found.toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right">
                <span className="inline-flex items-center gap-2">
                  {run.errors.length > 0 && (
                    <span
                      className="whitespace-nowrap rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700"
                      title={run.errors.join("\n")}
                    >
                      {run.errors.length} {run.errors.length === 1 ? "error" : "errors"}
                    </span>
                  )}
                  {runDownloadable(run) && (
                    <LinkButton
                      href={runDownloadUrl(run.run_id)}
                      size="sm"
                      onClick={(e) => e.stopPropagation()}
                      title="Download the Excel report"
                      icon={
                        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
                          <path d="M8 2v8m0 0L5 7m3 3l3-3M2.5 12.5h11" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      }
                    >
                      Download
                    </LinkButton>
                  )}
                </span>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}
