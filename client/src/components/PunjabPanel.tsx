"use client";

import { useEffect, useState } from "react";

import RunStatusPanel, { IdleRunSheet } from "@/components/RunStatus";
import PunjabResults from "@/components/PunjabResults";
import {
  Card,
  CheckboxField,
  ClosingRunwayField,
  ErrorBanner,
  LaunchBar,
  SearchSelect,
  SelectField,
  StartButton,
} from "@/components/ui";
import LiveMonitor from "@/components/LiveMonitor";
import StopButton from "@/components/StopButton";
import DateField from "@/components/DateField";
import RefreshButton from "@/components/RefreshButton";
import ScraperControls from "@/components/ScraperControls";
import SessionActivity from "@/components/SessionActivity";
import { usePortalSession } from "@/lib/usePortalSession";
import {
  getPunjabFilters,
  isRunActive,
  startPunjabScrape,
  type PpraFilterOptions,
} from "@/lib/api";

/** The site's id for its Sales/Auction/Disposal category. */
const AUCTION_TITLE_ID = "5";

type Dropdown = "procurement_type" | "procurement_title" | "department";

const NO_SELECTION: Record<Dropdown, string> = {
  procurement_type: "",
  procurement_title: "",
  department: "",
};

export default function PunjabPanel() {
  const [publishedFrom, setPublishedFrom] = useState("");
  const [publishedTo, setPublishedTo] = useState("");
  const [selected, setSelected] = useState(NO_SELECTION);
  const [closingRunwayDays, setClosingRunwayDays] = useState<number | null>(7);
  const [excludeAuctions, setExcludeAuctions] = useState(true);

  const [lists, setLists] = useState<PpraFilterOptions | null>(null);

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

  const handleStart = () => {
    if (publishedFrom && publishedTo && publishedFrom > publishedTo) {
      setError("Publish Date From must not be after To.");
      return;
    }
    return launch(() =>
      startPunjabScrape(
        {
          procurement_type: selected.procurement_type || null,
          procurement_title: selected.procurement_title || null,
          department: selected.department || null,
          published_from: publishedFrom || null,
          published_to: publishedTo || null,
        },
        {
          // An empty box means "filter off"; null days alone would fall back to 7.
          apply_closing_filter: closingRunwayDays !== null,
          closing_runway_days: closingRunwayDays,
          exclude_auctions: excludeAuctions,
        },
      ),
    );
  };

  const launchBar = (
    <LaunchBar summary="PPRA Punjab live tenders scraper ready with cooperative pause/resume and live tracking.">
      <>
        <StopButton run={run} onError={setError} />
        <LiveMonitor run={run} portal="punjab" />
        <ScraperControls run={run} onError={setError} onStatusChange={applyStatus} />
        <RefreshButton run={run} hasSession={hasSession} onReset={reset} />
        <StartButton onClick={handleStart} disabled={starting || isRunning} running={isRunning} starting={starting}>
          Start Punjab Scrape
        </StartButton>
      </>
    </LaunchBar>
  );

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}

      {/* Search sheet beside the run sheet on wide screens; stacked below that. */}
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_440px]">
      <Card
        footer={launchBar}
        title="PPRA Punjab Search & Filter Criteria"
        description="Reads every open tender from the Active Tenders page (eproc.punjab.gov.pk), then keeps the ones matching these filters."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Procurement Type"
            value={selected.procurement_type}
            options={options("procurement_type")}
            onChange={choose("procurement_type")}
            disabled={isRunning}
            placeholder="All Types"
          />
          <SelectField
            label="Procurement Title"
            value={selected.procurement_title}
            options={titleOptions}
            onChange={choose("procurement_title")}
            disabled={isRunning}
            placeholder="All Titles"
          />

          <div className="sm:col-span-2">
            <SearchSelect
              label="Department"
              value={selected.department}
              options={options("department")}
              onChange={choose("department")}
              disabled={isRunning}
              placeholder="All Departments"
            />
          </div>

          <div className="sm:col-span-2">
            <p className="mb-2 text-sm font-semibold text-ink-800" id="punjab-publish-range">Publish Date Range</p>
            <div className="grid gap-4 sm:grid-cols-2" role="group" aria-labelledby="punjab-publish-range">
              <DateField label="From" value={publishedFrom} onChange={setPublishedFrom} disabled={isRunning} />
              <DateField label="To" value={publishedTo} onChange={setPublishedTo} disabled={isRunning} />
            </div>
            <p className="mt-2 text-xs text-ink-500">
              Both days are included. Leave either blank for an open-ended range.
            </p>
          </div>
        </div>

        <ClosingRunwayField days={closingRunwayDays} onChange={setClosingRunwayDays} disabled={isRunning}>
          <CheckboxField
            label="Exclude Sales/Auction/Disposal"
            checked={excludeAuctions}
            onChange={toggleAuctions}
            disabled={isRunning}
          />
        </ClosingRunwayField>
      </Card>
      {run ? <RunStatusPanel run={run} /> : <IdleRunSheet portal="punjab" />}
      </div>


      <SessionActivity portal="punjab" />
      {run && <PunjabResults key={run.run_id} runId={run.run_id} />}
    </div>
  );
}
