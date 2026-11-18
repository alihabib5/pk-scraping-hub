"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { Portal } from "@/lib/api";
import { useLandingFacts } from "@/lib/landingFacts";
import { PORTALS, portalMeta, runSerial, runSerialShort } from "@/lib/portals";
import { formatTimestamp } from "@/lib/runs";

const HOSTS: Record<Portal, string> = {
  ppra: "epms.ppra.gov.pk",
  punjab: "eproc.punjab.gov.pk",
};

/**
 * The landing page's first viewport: one stamp-paper sheet carrying the offer
 * and the first step of the task (which portal), with the latest real run's
 * serial in its corner and live figures beside it. Choosing a portal and
 * continuing opens that portal's console, where the search is set; nothing
 * here starts a scrape.
 */
export default function IssueSheet() {
  const facts = useLandingFacts();
  const [portal, setPortal] = useState<Portal>("ppra");
  const latest = facts.latest;
  const total = facts.runCounts ? facts.runCounts.ppra + facts.runCounts.punjab : null;

  return (
    <div className="mx-auto grid w-full max-w-[1312px] gap-10 px-4 py-10 sm:px-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-12 lg:py-14 xl:px-16">
      <section aria-labelledby="landing-title" className="sheet-rule rounded-md bg-sheet px-7 pb-9 pt-10 shadow-[0_1px_0_var(--color-ink-200),0_18px_40px_-24px_rgba(18,64,47,0.35)] sm:px-12 sm:pb-11 sm:pt-12">
        {latest && (
          <Link
            href={`/console/${latest.scraper}/history`}
            className="inline-block rounded font-mono text-lg font-bold tracking-[0.06em] text-ink-900 underline decoration-ink-300 underline-offset-4 hover:decoration-intaglio-800"
            title="The most recent completed run, in its register"
          >
            <span className="sr-only">Latest run </span>
            {runSerial(latest.scraper, latest.run_id)}
          </Link>
        )}

        <h1
          id="landing-title"
          className="mt-5 text-balance text-[clamp(2.6rem,5.4vw,4.5rem)] font-extrabold leading-[1.02] tracking-[-0.03em] text-intaglio-950"
        >
          Every public bid.
          <br />
          <span className="text-intaglio-800">Found automatically.</span>
        </h1>
        <p className="mt-4 max-w-[38rem] text-pretty text-[17px] leading-relaxed text-ink-600">
          PK-Hub runs the PPRA tender searches you care about, collects every matching tender page by page, and hands
          you a spreadsheet, without anyone clicking through a government website.
        </p>

        <div className="mt-8 border-t border-ink-200 pt-6">
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-ink-800">Issue a run on</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {PORTALS.map((p) => {
                const size = facts.listSizes[p.key];
                return (
                  <label
                    key={p.key}
                    className={`flex cursor-pointer items-start gap-3 rounded-lg border bg-white px-4 py-3.5 transition has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-intaglio-700 ${
                      portal === p.key ? "border-intaglio-900 shadow-[inset_0_0_0_1px_var(--color-intaglio-900)]" : "border-ink-200 hover:border-ink-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="portal"
                      value={p.key}
                      checked={portal === p.key}
                      onChange={() => setPortal(p.key)}
                      className="mt-1 h-4 w-4 shrink-0"
                    />
                    <span className="min-w-0">
                      <span className="block text-[17px] font-bold text-ink-950">{p.label}</span>
                      <span className="block font-mono text-[12.5px] text-ink-600">
                        {HOSTS[p.key]}
                        {size && size.count > 0 && ` · ${size.count.toLocaleString()} ${size.noun}`}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
            <p id="issue-hint" className="max-w-sm text-sm text-ink-600">
              The console opens on {portalMeta(portal).label} with its full search form: keywords, closing dates and every
              filter the portal offers.
            </p>
            <Link
              href={`/console/${portal}`}
              className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-intaglio-900 px-6 text-base font-bold text-white shadow-sm shadow-intaglio-950/20 transition hover:bg-intaglio-800 active:scale-[0.98]"
            >
              Set up a run
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      <aside aria-label="Latest figures" className="self-start lg:pt-4">
        <h2 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-intaglio-800">
          {latest
            ? `Last issued · ${runSerialShort(latest.scraper, latest.run_id)} · ${formatTimestamp(latest.started_at).split(",")[0]}`
            : "Latest figures"}
        </h2>
        {latest ? (
          <dl className="grid grid-cols-3 gap-x-6 lg:grid-cols-1">
            <Figure value={latest.bids_found} label={`tenders read on ${portalMeta(latest.scraper).label}${latest.total_pages ? `, ${latest.total_pages} pages` : ""}`} />
            <Figure value={latest.bids_processed} label="kept after the run's filters" />
            {total !== null && facts.runCounts && (
              <Figure
                value={total}
                label={`runs on record: ${facts.runCounts.ppra} federal, ${facts.runCounts.punjab} Punjab`}
              />
            )}
          </dl>
        ) : (
          <p className="border-t border-ink-200 pt-4 text-sm text-ink-600">
            Figures appear here once the PK-Hub server is reachable.
          </p>
        )}
      </aside>
    </div>
  );
}

function Figure({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col-reverse border-t border-ink-200 py-4">
      <dt className="mt-1.5 text-[13px] leading-snug text-ink-600">{label}</dt>
      <dd className="font-mono text-[clamp(2rem,3.4vw,2.75rem)] font-bold leading-none tracking-tight text-ink-950">
        {value.toLocaleString()}
      </dd>
    </div>
  );
}
