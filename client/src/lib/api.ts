const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Portal = "ppra";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

// -- runs --------------------------------------------------------------------

/** `paused` is a running job parked at a checkpoint — it still holds its browser
 *  and its slot, so it is active, not terminal. Only completed, failed and
 *  stopped end a run. */
export type RunState = "pending" | "queued" | "running" | "paused" | "completed" | "failed" | "stopped";

export interface RunStatus {
  run_id: string;
  scraper: Portal;
  status: RunState;
  step: string;
  started_at: string;
  finished_at: string | null;
  /** What the portal said the search matched. */
  bids_found: number;
  /** Rows saved so far (after the closing filter). */
  bids_processed: number;
  errors: string[];
  /** Non-fatal notices, e.g. a page that would not load. */
  warnings?: string[];
  /** One-line description of the search, e.g. "category=Goods". */
  search?: string;
  options?: PpraOptionsPayload;
  current_page?: number;
  total_pages?: number | null;
  /** Tenders dropped for closing too soon, and kept despite an unreadable date. */
  skipped_closing?: number;
  kept_unverified?: number;
  /** Tenders dropped because their city is Karachi (live count). */
  skipped_city?: number;
  /** True once the workbook has been written. */
  excel_exported?: boolean;
  /** A run the user stopped that nevertheless kept what it had gathered;
   *  `partial_record_count` is how many rows made it. */
  partial_results?: boolean;
  partial_record_count?: number;
}

/** One row of `GET /runs` — the slice of a run the jobs bar needs. */
export interface Job {
  run_id: string;
  scraper: Portal;
  status: RunState;
  step: string;
  started_at: string;
  finished_at: string | null;
  bids_found: number;
  bids_processed: number;
  queue_position?: number;
  partial_results?: boolean;
  partial_record_count?: number;
  search?: string;
}

/** How many runs are executing, waiting, and allowed at once. */
export interface JobCapacity {
  running: number;
  queued: number;
  /** Parked jobs. Counted apart from `running` because they still hold a slot. */
  paused: number;
  capacity: number;
}

export interface JobLogLine {
  seq: number;
  ts: number | null;
  level: string;
  logger: string;
  message: string;
}

export function getJobs(activeOnly = true): Promise<{ jobs: Job[]; capacity: JobCapacity }> {
  return request(`/runs?active=${activeOnly}`);
}

export function getJobLogs(runId: string, after = 0): Promise<{ lines: JobLogLine[]; seq: number }> {
  return request(`/runs/${runId}/logs?after=${after}`);
}

export function getRunStatus(portal: Portal, runId: string): Promise<RunStatus> {
  return request(`/${portal}/scrape/status/${runId}`);
}

export function listRuns(portal: Portal): Promise<{ runs: RunStatus[] }> {
  return request(`/${portal}/scrape/runs`);
}

/** A live browser frame (base64 PNG) for an in-flight run, or null until one is available. */
export function getRunScreenshot(runId: string): Promise<{ screenshot: string | null }> {
  return request(`/runs/${runId}/screenshot`);
}

/** A run has reached a final state — the UI should stop polling it. */
export function isTerminalStatus(status: RunState): boolean {
  return status === "completed" || status === "failed" || status === "stopped";
}

/**
 * A run that still owns (or is waiting for) a browser and a slot, and so is
 * still the console's business: it can be paused, resumed, stopped and watched.
 * `queued` counts: a run waiting for a slot has not ended, and must keep being
 * polled until it starts.
 */
export function isRunActive(run: RunStatus | null | undefined): run is RunStatus {
  return (
    !!run &&
    (run.status === "pending" ||
      run.status === "queued" ||
      run.status === "running" ||
      run.status === "paused")
  );
}

/** Stop an in-flight run (a queued one is cancelled). 409 if it already finished. */
export function stopScrape(runId: string): Promise<{ stopped: boolean; run_id: string }> {
  return request(`/runs/${runId}/stop`, { method: "POST" });
}

/** Park a running job at its next page. It keeps its browser, so resuming
 *  continues exactly where it stopped. */
export function pauseScrape(runId: string): Promise<{ paused: boolean; run_id: string }> {
  return request(`/runs/${runId}/pause`, { method: "POST" });
}

/** Release a parked job. */
export function resumeScrape(runId: string): Promise<{ resumed: boolean; run_id: string }> {
  return request(`/runs/${runId}/resume`, { method: "POST" });
}

/** A finished (or stopped, partial) run's Excel workbook, as a browser download. */
export function runDownloadUrl(runId: string): string {
  return `${API_URL}/runs/${runId}/download`;
}

/** FastAPI's generated interactive reference, served by the backend at /docs. */
export function apiDocsUrl(): string {
  return `${API_URL}/docs`;
}

// -- PPRA --------------------------------------------------------------------

/** One dropdown option on the PPRA search form. `value` is the site's own id —
 *  the only thing its search accepts; names are ignored or match nothing. */
export interface FilterOption {
  value: string;
  label: string;
}

/** The site's dropdowns by the query parameter each sets: tender_type,
 *  tender_method, procurement_category, sector, tender_nature, organization,
 *  country, status. */
export interface PpraFilterOptions {
  options: Partial<Record<string, FilterOption[]>>;
  /** When the lists were last read from the site; null while the built-in copy is served. */
  refreshed_at: string | null;
  source: "site" | "seed";
}

export function getPpraFilters(): Promise<PpraFilterOptions> {
  return request("/ppra/filters");
}

/** Re-read the dropdowns from the live site now. */
export function refreshPpraFilters(): Promise<PpraFilterOptions> {
  return request("/ppra/filters/refresh", { method: "POST" });
}

/** Dropdown fields carry the site's option ids. */
export interface PpraFiltersPayload {
  keyword?: string | null;
  tender_number?: string | null;
  closing_date?: string | null;
  tender_type?: string | null;
  tender_method?: string | null;
  category?: string | null;
  sector?: string | null;
  nature?: string | null;
  organization?: string | null;
  country?: string | null;
  advertise_from?: string | null;
  advertise_to?: string | null;
  status?: string | null;
  city?: string | null;
}

export interface PpraOptionsPayload {
  /** False turns the closing-date filter off; otherwise it is on. */
  apply_closing_filter?: boolean | null;
  /** Minimum days until closing (0–365); null uses the server default of 7. */
  closing_runway_days?: number | null;
  /** Drop tenders located in Karachi. */
  exclude_karachi?: boolean;
  delay_ms?: number | null;
}

/** One stored tender, as `GET /ppra/bids` returns it. */
export interface PpraBid {
  id: number;
  run_id: string;
  tender_no: string;
  title: string;
  organization: string | null;
  sector: string | null;
  city: string | null;
  status: string | null;
  closing_at: string | null;
  detail_url: string | null;
}

export function startPpraScrape(
  filters: PpraFiltersPayload = {},
  options: PpraOptionsPayload = {},
  livePreview = false
): Promise<{ run_id: string; search: string }> {
  return request("/ppra/scrape", {
    method: "POST",
    body: JSON.stringify({ filters, options, live_preview: livePreview }),
  });
}

export function listPpraBids(params: {
  run_id?: string;
  query?: string;
  after_id?: number;
  limit?: number;
}): Promise<{ bids: PpraBid[]; count: number }> {
  const q = new URLSearchParams();
  if (params.run_id) q.set("run_id", params.run_id);
  if (params.query) q.set("query", params.query);
  if (params.after_id !== undefined) q.set("after_id", String(params.after_id));
  if (params.limit !== undefined) q.set("limit", String(params.limit));
  return request(`/ppra/bids?${q.toString()}`);
}
