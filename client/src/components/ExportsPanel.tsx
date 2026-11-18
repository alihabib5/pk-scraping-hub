"use client";

import { useEffect, useState } from "react";

import { Button, DataTable, EmptyState, ErrorBanner, LinkButton, Spinner } from "@/components/ui";
import { runDownloadUrl } from "@/lib/api";
import { fetchRunsState, formatTimestamp, runDownloadable, runTarget, RUNS_LOADING, type RunsState } from "@/lib/runs";
import { runSerial, type PortalMeta } from "@/lib/portals";

/** Per-run Excel downloads for past runs (`GET /runs/{id}/download`). */
export default function ExportsPanel({ meta }: { meta: PortalMeta }) {
  const [{ runs, error, loading }, setState] = useState<RunsState>(RUNS_LOADING);

  useEffect(() => {
    let cancelled = false;
    fetchRunsState(meta.key, "downloads").then((next) => {
      if (!cancelled) setState(next);
    });
    return () => {
      cancelled = true;
    };
  }, [meta.key]);

  const refresh = () => {
    setState((s) => ({ ...s, loading: true }));
    fetchRunsState(meta.key, "downloads").then(setState);
  };

  const downloadable = (runs ?? []).filter(runDownloadable);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink-950">Downloads</h1>
          <p className="mt-1 text-sm text-ink-600">
            {`Every completed ${meta.label} run as its Excel report.`}
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
          Loading downloads…
        </div>
      )}

      {runs !== null && downloadable.length === 0 && !error && (
        <EmptyState
          icon={
            <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
              <path d="M10 3v9m0 0l-3.5-3.5M10 12l3.5-3.5M4 16.5h12" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          }
          title="Nothing to download yet"
          description={`Runs that finish successfully can be downloaded here. Start a ${meta.label} scrape from the Console to produce one.`}
        />
      )}

      {runs !== null && downloadable.length > 0 && (
        <DataTable
          caption={`${downloadable.length} ${downloadable.length === 1 ? "download" : "downloads"}`}
          headers={[
            { label: "Serial" },
            { label: "Produced" },
            { label: "Searched for" },
            { label: "Bids", className: "text-right" },
            { label: "", className: "text-right" },
          ]}
        >
          {downloadable.map((run) => {
            return (
              <tr key={run.run_id} className="transition hover:bg-intaglio-50">
                <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[13px] font-bold text-ink-950">
                  {runSerial(run.scraper, run.run_id)}
                </td>
                <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-ink-700">
                  {formatTimestamp(run.finished_at ?? run.started_at)}
                </td>
                <td className="max-w-xs truncate px-4 py-2.5 text-ink-800" title={runTarget(run)}>
                  {runTarget(run)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-ink-900">{run.bids_found.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right">
                  <LinkButton
                    href={runDownloadUrl(run.run_id)}
                    size="sm"
                    icon={
                      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
                        <path d="M8 2v8m0 0L5 7m3 3l3-3M2.5 12.5h11" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    }
                  >
                    Download Excel
                  </LinkButton>
                </td>
              </tr>
            );
          })}
        </DataTable>
      )}
    </div>
  );
}
