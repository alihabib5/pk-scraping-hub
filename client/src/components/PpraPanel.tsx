"use client";

import { useEffect, useState } from "react";

import RunStatusPanel from "@/components/RunStatus";
import PpraResults from "@/components/PpraResults";
import {
  Card,
  ErrorBanner,
  Field,
  LaunchBar,
  SearchSelect,
  SelectField,
  StartButton,
} from "@/components/ui";
import LiveMonitor from "@/components/LiveMonitor";
import StopButton from "@/components/StopButton";
import RefreshButton from "@/components/RefreshButton";
import ScraperControls from "@/components/ScraperControls";
import SessionActivity from "@/components/SessionActivity";
import { usePortalSession } from "@/lib/usePortalSession";
import { formatTimestamp } from "@/lib/runs";
import {
  getPpraFilters,
  isRunActive,
  refreshPpraFilters,
  startPpraScrape,
  type PpraFilterOptions,
} from "@/lib/api";

/** The dropdowns, by the search form field each one fills. Values are the
 *  site's option ids — the only thing its search accepts. */
type Dropdown =
  | "tender_type"
  | "tender_method"
  | "category"
  | "sector"
  | "nature"
  | "organization"
  | "country"
  | "status";

/** Which of the site's option lists feeds each dropdown. */
const OPTION_KIND: Record<Dropdown, string> = {
  tender_type: "tender_type",
  tender_method: "tender_method",
  category: "procurement_category",
  sector: "sector",
  nature: "tender_nature",
  organization: "organization",
  country: "country",
  status: "status",
};

const NO_SELECTION: Record<Dropdown, string> = {
  tender_type: "",
  tender_method: "",
  category: "",
  sector: "",
  nature: "",
  organization: "",
  country: "",
  status: "",
};

export default function PpraPanel() {
  const [keyword, setKeyword] = useState("");
  const [tenderNumber, setTenderNumber] = useState("");
  const [closingDate, setClosingDate] = useState("");
  const [advertiseFrom, setAdvertiseFrom] = useState("");
  const [advertiseTo, setAdvertiseTo] = useState("");
  const [city, setCity] = useState("");
  const [selected, setSelected] = useState(NO_SELECTION);
  const [closingRunwayDays, setClosingRunwayDays] = useState<number | null>(7);
  const [excludeKarachi, setExcludeKarachi] = useState(false);

  const [lists, setLists] = useState<PpraFilterOptions | null>(null);
  const [refreshingLists, setRefreshingLists] = useState(false);

  const { run, error, starting, setError, launch, applyStatus, hasSession, reset } =
    usePortalSession("ppra");

  const isRunning = isRunActive(run);

  useEffect(() => {
    let cancelled = false;
    getPpraFilters()
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
      setLists(await refreshPpraFilters());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshingLists(false);
    }
  };

  const options = (field: Dropdown) => lists?.options[OPTION_KIND[field]] ?? [];
  const choose = (field: Dropdown) => (value: string) => setSelected((s) => ({ ...s, [field]: value }));
  const dropdown = (field: Dropdown, label: string, placeholder: string) => (
    <SelectField
      label={label}
      value={selected[field]}
      options={options(field)}
      onChange={choose(field)}
      disabled={isRunning}
      placeholder={placeholder}
    />
  );

  const handleStart = () =>
    launch(() =>
      startPpraScrape(
        {
          keyword: keyword.trim() || null,
          tender_number: tenderNumber.trim() || null,
          closing_date: closingDate || null,
          tender_type: selected.tender_type || null,
          tender_method: selected.tender_method || null,
          category: selected.category || null,
          sector: selected.sector || null,
          nature: selected.nature || null,
          organization: selected.organization || null,
          country: selected.country || null,
          advertise_from: advertiseFrom || null,
          advertise_to: advertiseTo || null,
          status: selected.status || null,
          city: city.trim() || null,
        },
        {
          // An empty box means "filter off"; null days alone would fall back to 7.
          apply_closing_filter: closingRunwayDays !== null,
          closing_runway_days: closingRunwayDays,
          exclude_karachi: excludeKarachi,
        },
      ),
    );

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}

      <Card
        title="PPRA Search & Filter Criteria"
        description="Filter active federal tenders published by the Public Procurement Regulatory Authority (epms.ppra.gov.pk)."
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
              title="Re-read every dropdown from epms.ppra.gov.pk"
              className="rounded-md px-2 py-1 font-medium text-ink-600 transition hover:bg-ink-50 hover:text-ink-900 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {refreshingLists ? "Refreshing…" : "Refresh lists"}
            </button>
          </div>
        }
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <Field
            label="Keyword Search"
            value={keyword}
            onChange={setKeyword}
            disabled={isRunning}
            placeholder="Title, description or tender no"
          />
          <Field
            label="Tender Number"
            value={tenderNumber}
            onChange={setTenderNumber}
            disabled={isRunning}
            placeholder="e.g. TS0000015884E"
          />
          <Field
            label="Closing Date"
            type="date"
            value={closingDate}
            onChange={setClosingDate}
            disabled={isRunning}
          />

          {dropdown("tender_type", "Tender Type", "All Types")}
          {dropdown("tender_method", "Method", "All Methods")}
          {dropdown("category", "Category", "All Categories")}
          {dropdown("sector", "Sector", "All Sectors")}
          {dropdown("nature", "Nature", "All")}
          {dropdown("status", "Status", "All Statuses")}

          <div className="sm:col-span-2">
            <SearchSelect
              label="Organization / Ministry"
              value={selected.organization}
              options={options("organization")}
              onChange={choose("organization")}
              disabled={isRunning}
              placeholder="All Organizations"
            />
          </div>
          <SearchSelect
            label="Country"
            value={selected.country}
            options={options("country")}
            onChange={choose("country")}
            disabled={isRunning}
            placeholder="All Countries"
          />

          <Field
            label="Advertise Date From"
            type="date"
            value={advertiseFrom}
            onChange={setAdvertiseFrom}
            disabled={isRunning}
          />
          <Field
            label="Advertise Date To"
            type="date"
            value={advertiseTo}
            onChange={setAdvertiseTo}
            disabled={isRunning}
          />
          <Field
            label="City"
            value={city}
            onChange={setCity}
            disabled={isRunning}
            placeholder="e.g. Islamabad, Lahore, Karachi"
          />
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
              checked={excludeKarachi}
              onChange={(e) => setExcludeKarachi(e.target.checked)}
              disabled={isRunning}
              className="h-4 w-4 rounded border-ink-300"
            />
            Exclude Karachi
          </label>
        </div>
      </Card>

      <LaunchBar summary="PPRA active tenders scraper ready with cooperative pause/resume and live tracking.">
        <div className="flex items-center gap-2">
          <StopButton run={run} onError={setError} />
          <LiveMonitor run={run} portal="ppra" />
          <ScraperControls run={run} onError={setError} onStatusChange={applyStatus} />
          <RefreshButton run={run} hasSession={hasSession} onReset={reset} />
          <StartButton
            onClick={handleStart}
            disabled={starting || isRunning}
            running={isRunning}
            starting={starting}
          >
            Start PPRA Scrape
          </StartButton>
        </div>
      </LaunchBar>

      {run && <RunStatusPanel run={run} />}
      <SessionActivity portal="ppra" />
      {run && <PpraResults key={run.run_id} runId={run.run_id} />}
    </div>
  );
}
