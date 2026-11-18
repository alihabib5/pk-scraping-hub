"use client";

import Rosette from "@/components/Rosette";
import { isRunActive, runDownloadUrl, type Portal, type RunStatus as RunStatusData } from "@/lib/api";
import { LinkButton, RunBadge } from "@/components/ui";
import { portalMeta, runSerial } from "@/lib/portals";
import { runDownloadable, runPartial } from "@/lib/runs";

const STEP_LABELS: Record<string, string> = {
  queued: "Queued",
  starting: "Starting the browser",
  opening_site: "Opening epms.ppra.gov.pk",
  opening_punjab: "Opening eproc.punjab.gov.pk",
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

  // Serial red belongs to the run in flight; a finished run prints in ink.
  const live = isRunActive(run);

  return (
    <section className="@container overflow-hidden rounded-xl border border-ink-200 bg-sheet shadow-sm shadow-ink-900/[0.03]">
      <header className="px-5 pb-1 pt-4">
        <div className="flex items-start justify-between gap-3">
          <h2
            className={`font-mono text-lg font-bold tracking-wide sm:text-xl ${live ? "text-serial-600" : "text-ink-900"}`}
          >
            <span className="sr-only">Run </span>
            {runSerial(run.scraper, run.run_id)}
          </h2>
          <RunBadge status={run.status} partial={run.partial_results} />
        </div>
        <p className="mt-1 truncate text-xs text-ink-600" title={run.search}>
          {portalMeta(run.scraper).label} · {run.search || "All active tenders"}
        </p>
      </header>

      {/* The rosette: one ring per page read. Counts beside it at poster scale. */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4">
        <Rosette read={run.current_page ?? 0} total={run.total_pages} live={live && !parked} size={120} />
        <dl className="grid min-w-0 flex-1 basis-56 grid-cols-2 gap-x-4 gap-y-3 @3xl:grid-cols-4">
          <Stat label="Tenders found" value={run.bids_found} />
          <Stat label="Saved" value={run.bids_processed} />
          <Stat
            label="Pages"
            value={run.total_pages ? `${run.current_page ?? 0}/${run.total_pages}` : "—"}
            muted={!run.total_pages}
          />
          <Stat label="Excel" value={run.excel_exported ? "Ready" : "—"} muted={!run.excel_exported} />
        </dl>
      </div>

      {parked && (
        <div className="border-y border-amber-200 bg-amber-50 px-5 py-3.5">
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

      {/* The backend reports steps, not percentages: the rosette counts pages,
          this line says what the scraper is doing now. */}
      {inFlight && (
        <div className="mx-5 mb-4 flex items-center gap-2.5 rounded-lg border border-dashed border-ink-300 bg-white px-3 py-2.5">
          <span className="status-pulse h-2 w-2 shrink-0 rounded-full bg-serial-600" aria-hidden />
          <span className="text-sm font-medium text-ink-800">{stepLabel(run.step)}</span>
        </div>
      )}

      {(run.errors.length > 0 || warnings.length > 0 || run.status === "completed" || run.status === "stopped" || runway !== undefined) && (
        <div className="space-y-3 border-t border-ink-200 p-5">
          {/* What the run's own filters did: one ruled line each. */}
          {(runway !== undefined || run.options?.exclude_karachi || run.options?.exclude_auctions) && (
            <ul className="divide-y divide-ink-200 border-y border-ink-200">
              {runway !== undefined && (
                <ClosingFilterNote
                  minDays={runway}
                  skipped={run.skipped_closing ?? 0}
                  unreadable={run.kept_unverified ?? 0}
                />
              )}
              {run.options?.exclude_karachi && (
                <FilterRow label="Karachi tenders · excluded">
                  {(run.skipped_city ?? 0) > 0
                    ? `${run.skipped_city} Karachi ${run.skipped_city === 1 ? "tender was" : "tenders were"} dropped.`
                    : "No Karachi tenders found so far."}
                </FilterRow>
              )}
              {run.options?.exclude_auctions && (
                <FilterRow label="Sales/Auction/Disposal · excluded">
                  {(run.skipped_auction ?? 0) > 0
                    ? `${run.skipped_auction} ${run.skipped_auction === 1 ? "tender was" : "tenders were"} removed.`
                    : "None found so far."}
                </FilterRow>
              )}
            </ul>
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
                  <li key={i} className="text-[13px] leading-relaxed">
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
                  <li key={i} className="text-[13px] leading-relaxed">
                    {warning}
                  </li>
                ))}
              </ul>
            </Notice>
          )}

          {download && (
            <div
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border px-3 py-2.5 ${
                partial ? "border-amber-300 bg-amber-50" : "border-intaglio-200 bg-intaglio-50"
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
    <div className="flex min-w-0 flex-col-reverse">
      <dt className="mt-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-600">{label}</dt>
      <dd
        className={`truncate font-mono text-[40px] font-bold leading-none tracking-tight ${muted ? "text-ink-300" : "text-ink-950"}`}
        title={String(value)}
      >
        {typeof value === "number" ? value.toLocaleString() : value}
      </dd>
    </div>
  );
}

/** The run sheet before anything has been issued on this portal. */
export function IdleRunSheet({ portal }: { portal: Portal }) {
  return (
    <section className="rounded-xl border border-dashed border-ink-300 bg-sheet/70 px-5 py-6">
      <p className="font-mono text-lg font-bold tracking-wide text-ink-300">{portalMeta(portal).code} · —</p>
      <div className="mt-4 flex items-center gap-5">
        <Rosette read={0} total={null} live={false} size={112} />
        <div>
          <h2 className="font-display text-[15px] text-ink-900">No run issued yet</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-600">
            Set the search and press Start. The run gets a serial, and the rosette draws one ring for every page it
            reads.
          </p>
        </div>
      </div>
    </section>
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
    <FilterRow label={minDays === null ? "Closing-date filter · off" : `Closing-date filter · ≥ ${minDays} days out`}>
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
    </FilterRow>
  );
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <li className="flex flex-wrap gap-x-2 gap-y-0.5 py-2.5 text-[13px] leading-relaxed">
      <span className="font-semibold text-ink-900">{label}</span>
      <span className="text-ink-600">{children}</span>
    </li>
  );
}
