"use client";

import { runDownloadUrl, type RunStatus as RunStatusData } from "@/lib/api";
import { LinkButton, RunBadge } from "@/components/ui";
import { runDownloadable, runPartial } from "@/lib/runs";

const STEP_LABELS: Record<string, string> = {
  queued: "Queued",
  starting: "Starting the browser",
  opening_site: "Opening epms.ppra.gov.pk",
  scraping_pages: "Reading the results",
  packaging_results: "Saving the Excel report",
  completed: "Done",
  failed: "Failed",
  stopped: "Stopped by you",
  interrupted: "Interrupted by a server restart",
};

export function stepLabel(step: string): string {
  const page = /^page_(\d+)_of_(\d+)$/.exec(step);
  if (page) return `Reading page ${page[1]} of ${page[2]}`;
  if (step.startsWith("queued (")) return `Waiting for a free slot ${step.slice("queued ".length)}`;
  return STEP_LABELS[step] ?? step;
}

export default function RunStatus({ run }: { run: RunStatusData }) {
  const inFlight = run.status === "running" || run.status === "pending" || run.status === "queued";
  // Parked, not finished. It gets its own line rather than the spinner: an
  // animation on a run that is deliberately doing nothing reads as a hang.
  const parked = run.status === "paused";
  const download = runDownloadable(run);
  // A stopped run that kept its rows. The panel says so rather than dressing it
  // up as a finished one: the spreadsheet is missing everything after Stop.
  const partial = runPartial(run);
  const runway = closingRunway(run);
  const warnings = run.warnings ?? [];

  return (
    <section className="overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-100 px-5 py-3.5">
        <div className="flex min-w-0 items-center gap-2.5">
          <h3 className="text-sm font-semibold text-ink-900">Run status</h3>
          {run.search && <span className="truncate text-sm text-ink-500">{run.search}</span>}
        </div>
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs text-ink-400">{run.run_id}</span>
          <RunBadge status={run.status} partial={run.partial_results} />
        </div>
      </header>

      {parked && (
        <div className="border-b border-amber-200 bg-amber-50 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <span className="h-3.5 w-3.5 shrink-0 rounded-full border-2 border-amber-400" aria-hidden />
            <span className="text-sm font-medium text-amber-900">
              Paused at {stepLabel(run.step)}
            </span>
          </div>
          <p className="mt-1.5 text-xs text-amber-800">
            The browser and the slot are still held. Resume from the toolbar above to
            continue at the next page — nothing is re-collected.
          </p>
        </div>
      )}

      {/* The backend reports steps, not percentages, so no fake completion %. */}
      {inFlight && (
        <div className="border-b border-ink-100 bg-ink-50/70 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-gold-200 border-t-gold-600" />
            <span className="text-sm font-medium text-ink-700">{stepLabel(run.step)}</span>
          </div>
          <div className="mt-2.5 h-1 overflow-hidden rounded-full bg-ink-200">
            <div className="progress-slide h-full w-1/4 rounded-full bg-gold-500" />
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 divide-ink-100 sm:grid-cols-4 sm:divide-x">
        <Stat label="Tenders found" value={run.bids_found} />
        <Stat label="Saved" value={run.bids_processed} />
        <Stat
          label="Pages"
          value={run.total_pages ? `${run.current_page ?? 0} / ${run.total_pages}` : "—"}
          muted={!run.total_pages}
        />
        <Stat label="Results" value={run.excel_exported ? "Ready" : "—"} muted={!run.excel_exported} />
      </div>

      {(run.errors.length > 0 || warnings.length > 0 || run.status === "completed" || run.status === "stopped" || runway !== undefined) && (
        <div className="space-y-3 border-t border-ink-100 p-5">
          {runway !== undefined && (
            <ClosingFilterNote
              minDays={runway}
              skipped={run.skipped_closing ?? 0}
              unreadable={run.kept_unverified ?? 0}
            />
          )}

          {run.options?.exclude_karachi && (
            <div className="rounded-lg border border-ink-200 bg-ink-50 p-3.5">
              <p className="mb-1 text-xs font-semibold text-ink-700">Karachi tenders · excluded</p>
              <p className="text-sm text-ink-600">
                {(run.skipped_city ?? 0) > 0
                  ? `${run.skipped_city} Karachi ${run.skipped_city === 1 ? "tender was" : "tenders were"} dropped.`
                  : "No Karachi tenders found so far."}
              </p>
            </div>
          )}

          {run.status === "stopped" && (
            <Notice tone="amber" title="Stopped">
              You stopped this run{run.bids_processed > 0 ? ` after ${run.bids_processed} saved` : ""}. Anything captured before the stop is kept below.
            </Notice>
          )}

          {run.errors.length > 0 && (
            <Notice tone="red" title={`${run.errors.length} ${run.errors.length === 1 ? "error" : "errors"}`}>
              <ul className="max-h-28 space-y-1 overflow-y-auto">
                {run.errors.map((error, i) => (
                  <li key={i} className="font-mono text-xs leading-relaxed">
                    {error}
                  </li>
                ))}
              </ul>
            </Notice>
          )}

          {warnings.length > 0 && (
            <Notice tone="amber" title={`${warnings.length} ${warnings.length === 1 ? "notice" : "notices"}`}>
              <ul className="max-h-28 space-y-1 overflow-y-auto">
                {warnings.map((warning, i) => (
                  <li key={i} className="font-mono text-xs leading-relaxed">
                    {warning}
                  </li>
                ))}
              </ul>
            </Notice>
          )}

          {download && (
            <div
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border px-3 py-2.5 ${
                partial ? "border-amber-300 bg-amber-50" : "border-ink-200 bg-ink-50"
              }`}
            >
              <div className="min-w-0">
                <p className={`text-xs font-medium ${partial ? "text-amber-900" : "text-ink-600"}`}>
                  {partial ? "Partial results ready" : "Results ready"}
                </p>
                <p className={`text-xs ${partial ? "text-amber-800" : "text-ink-500"}`}>
                  {partial
                    ? `You stopped this run, so it covers only what it had found by then${
                        typeof run.partial_record_count === "number"
                          ? ` — ${run.partial_record_count.toLocaleString()} record${run.partial_record_count === 1 ? "" : "s"}`
                          : ""
                      }.`
                    : "The Excel report — this run's complete output."}
                </p>
              </div>
              <LinkButton href={runDownloadUrl(run.run_id)} variant="primary" size="sm" icon={<DownloadIcon />}>
                Download Excel
              </LinkButton>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/** The run's closing-date runway: days, null when the filter was off, or
 *  undefined while the run's options aren't known. Mirrors the server's
 *  `PpraOptions.get_runway_days`. */
function closingRunway(run: RunStatusData): number | null | undefined {
  const options = run.options;
  if (!options) return undefined;
  if (options.closing_runway_days != null) return options.closing_runway_days;
  return options.apply_closing_filter === false ? null : 7;
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M8 2v8m0 0L5 7m3 3l3-3M2.5 12.5h11" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Stat({ label, value, muted }: { label: string; value: string | number; muted?: boolean }) {
  return (
    <div className="border-b border-ink-100 px-5 py-4 sm:border-b-0">
      <div className="text-xs font-medium text-ink-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${muted ? "text-ink-300" : "text-ink-900"}`}>{value}</div>
    </div>
  );
}

function Notice({
  tone,
  title,
  children,
}: {
  tone: "red" | "amber";
  title: string;
  children: React.ReactNode;
}) {
  const cls = {
    red: { box: "border-red-200 bg-red-50", head: "text-red-800", body: "text-red-700" },
    amber: { box: "border-amber-200 bg-amber-50", head: "text-amber-800", body: "text-amber-700" },
  }[tone];

  return (
    <div className={`rounded-lg border p-3.5 ${cls.box}`}>
      <p className={`mb-1 text-xs font-semibold ${cls.head}`}>{title}</p>
      <div className={`text-sm ${cls.body}`}>{children}</div>
    </div>
  );
}

/** What the closing-date filter did on this run. */
function ClosingFilterNote({
  minDays,
  skipped,
  unreadable,
}: {
  minDays: number | null;
  skipped: number;
  unreadable: number;
}) {
  return (
    <div className="rounded-lg border border-ink-200 bg-ink-50 p-3.5">
      <p className="mb-1 text-xs font-semibold text-ink-700">
        {minDays === null ? "Closing-date filter · off" : `Closing-date filter · ≥ ${minDays} days out`}
      </p>
      <p className="text-sm text-ink-600">
        {minDays === null
          ? "Every tender is kept, whatever its closing date."
          : `Only tenders closing at least ${minDays} days from today are kept.${
              skipped > 0
                ? ` ${skipped} closing sooner ${skipped === 1 ? "was" : "were"} skipped.`
                : " None were closing sooner."
            }${
              unreadable > 0
                ? ` ${unreadable} with an unreadable close date ${unreadable === 1 ? "was" : "were"} kept.`
                : ""
            }`}
      </p>
    </div>
  );
}
