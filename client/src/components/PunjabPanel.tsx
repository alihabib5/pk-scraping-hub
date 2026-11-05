"use client";

import { useEffect, useState } from "react";

import RunStatusPanel from "@/components/RunStatus";
import PunjabResults from "@/components/PunjabResults";
import { Card, ErrorBanner, LaunchBar, SearchSelect, SelectField, StartButton } from "@/components/ui";
import LiveMonitor from "@/components/LiveMonitor";
import StopButton from "@/components/StopButton";
import DateField from "@/components/DateField";
import RefreshButton from "@/components/RefreshButton";
import ScraperControls from "@/components/ScraperControls";
import SessionActivity from "@/components/SessionActivity";
import { usePortalSession } from "@/lib/usePortalSession";
import { formatTimestamp } from "@/lib/runs";
import {
  getPunjabFilters,
  isRunActive,
  refreshPunjabFilters,
  startPunjabScrape,
  type PpraFilterOptions,
} from "@/lib/api";

/** The site's id for its Sales/Auction/Disposal category. */
const AUCTION_TITLE_ID = "5";

type Dropdown = "procurement_type" | "procurement_category" | "procurement_title" | "department";

const NO_SELECTION: Record<Dropdown, string> = {
  procurement_type: "",
  procurement_category: "",
  procurement_title: "",
  department: "",
};

export default function PunjabPanel() {
  const [closingFrom, setClosingFrom] = useState("");
  const [closingTo, setClosingTo] = useState("");
  const [selected, setSelected] = useState(NO_SELECTION);
  const [closingRunwayDays, setClosingRunwayDays] = useState<number | null>(7);
  const [excludeAuctions, setExcludeAuctions] = useState(true);

  const [lists, setLists] = useState<PpraFilterOptions | null>(null);
  const [refreshingLists, setRefreshingLists] = useState(false);

  const { run, error, starting, setError, launch, applyStatus, hasSession, reset } =
    usePortalSession("punjab");

  const isRunning = isRunActive(run);

  useEffect(() => {
    let cancelled = false;
    getPunjabFilters()
      .then((next) => {
        if (!cancelled) setLists(next);
      })
      .catch((e) => {
        if (!cancelled) setError(`Could not load the filter lists — is the API running? (${(e as Error).message})`);
      });
    return () => {
      cancelled = true;
    };
  }, [setError]);

  const reloadLists = async () => {
    setRefreshingLists(true);
    try {
      setLists(await refreshPunjabFilters());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshingLists(false);
    }
  };

  const options = (field: Dropdown) => lists?.options[field] ?? [];
  const choose = (field: Dropdown) => (value: string) => setSelected((s) => ({ ...s, [field]: value }));
  // With auctions excluded, searching only auctions could return nothing.
  const titleOptions = options("procurement_title").filter(
    (o) => !excludeAuctions || o.value !== AUCTION_TITLE_ID,
  );

  const toggleAuctions = (exclude: boolean) => {
    setExcludeAuctions(exclude);
    if (exclude) {
      setSelected((s) =>
        s.procurement_title === AUCTION_TITLE_ID ? { ...s, procurement_title: "" } : s,
      );
    }
  };

  const handleStart = () =>
    launch(() =>
      startPunjabScrape(
        {
          procurement_type: selected.procurement_type || null,
          procurement_category: selected.procurement_category || null,
          procurement_title: selected.procurement_title || null,
          department: selected.department || null,
          closing_from: closingFrom || null,
          closing_to: closingTo || null,
        },
        {
          // An empty box means "filter off"; null days alone would fall back to 7.
          apply_closing_filter: closingRunwayDays !== null,
          closing_runway_days: closingRunwayDays,
          exclude_auctions: excludeAuctions,
        },
      ),
    );

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}

      <Card
        title="PPRA Punjab Search & Filter Criteria"
        description="Filter live tenders on the Punjab e-Procurement portal (eproc.punjab.gov.pk). With no closing dates, every tender closing from today onward is searched."
        actions={
          <div className="flex items-center gap-2 text-xs text-ink-500">
            <span>
              {!lists
                ? "Loading lists…"
                : lists.refreshed_at
                  ? `Lists from the site, ${formatTimestamp(lists.refreshed_at)}`
                  : "Built-in lists"}
            </span>
            <button
              type="button"
              onClick={reloadLists}
              disabled={refreshingLists || isRunning}
              title="Re-read every dropdown from eproc.punjab.gov.pk"
              className="rounded-md px-2 py-1 font-medium text-ink-600 transition hover:bg-ink-50 hover:text-ink-900 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {refreshingLists ? "Refreshing…" : "Refresh lists"}
            </button>
          </div>
        }
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <SelectField
            label="Procurement Type"
            value={selected.procurement_type}
            options={options("procurement_type")}
            onChange={choose("procurement_type")}
            disabled={isRunning}
            placeholder="All Types"
          />
          <SelectField
            label="Category"
            value={selected.procurement_category}
            options={options("procurement_category")}
            onChange={choose("procurement_category")}
            disabled={isRunning}
            placeholder="All Categories"
          />
          <SelectField
            label="Procurement Title"
            value={selected.procurement_title}
            options={titleOptions}
            onChange={choose("procurement_title")}
            disabled={isRunning}
            placeholder="All Titles"
          />

          <div className="sm:col-span-3">
            <SearchSelect
              label="Department"
              value={selected.department}
              options={options("department")}
              onChange={choose("department")}
              disabled={isRunning}
              placeholder="All Departments"
            />
          </div>

          <DateField label="Closing Date From" value={closingFrom} onChange={setClosingFrom} disabled={isRunning} />
          <DateField label="Closing Date To" value={closingTo} onChange={setClosingTo} disabled={isRunning} />
        </div>

        <div className="mt-4 flex items-center gap-3 border-t border-ink-100 pt-4">
          <label className="shrink-0 text-xs font-medium text-ink-700">Min. days until closing</label>
          <input
            type="number"
            min={0}
            max={365}
            value={closingRunwayDays ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setClosingRunwayDays(v === "" ? null : Math.min(365, Math.max(0, parseInt(v, 10) || 0)));
            }}
            disabled={isRunning}
            placeholder="off"
            className="w-24 rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs text-ink-800 focus:border-ink-400 focus:outline-none"
          />
          <span className="text-xs text-ink-500">
            {closingRunwayDays === null
              ? "Filter off — all tenders included"
              : closingRunwayDays === 0
                ? "All tenders (0-day minimum)"
                : `Skip tenders closing in < ${closingRunwayDays} day${closingRunwayDays !== 1 ? "s" : ""}`}
          </span>
          <label className="ml-auto flex items-center gap-2 text-xs font-medium text-ink-700">
            <input
              type="checkbox"
              checked={excludeAuctions}
              onChange={(e) => toggleAuctions(e.target.checked)}
              disabled={isRunning}
              className="h-4 w-4 rounded border-ink-300"
            />
            Exclude Sales/Auction/Disposal
          </label>
        </div>
      </Card>

      <LaunchBar summary="PPRA Punjab live tenders scraper ready with cooperative pause/resume and live tracking.">
        <div className="flex items-center gap-2">
          <StopButton run={run} onError={setError} />
          <LiveMonitor run={run} portal="punjab" />
          <ScraperControls run={run} onError={setError} onStatusChange={applyStatus} />
          <RefreshButton run={run} hasSession={hasSession} onReset={reset} />
          <StartButton onClick={handleStart} disabled={starting || isRunning} running={isRunning} starting={starting}>
            Start Punjab Scrape
          </StartButton>
        </div>
      </LaunchBar>

      {run && <RunStatusPanel run={run} />}
      <SessionActivity portal="punjab" />
      {run && <PunjabResults key={run.run_id} runId={run.run_id} />}
    </div>
  );
}
