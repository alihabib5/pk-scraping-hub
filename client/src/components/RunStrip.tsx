"use client";

import { Fragment } from "react";

import Rosette from "@/components/Rosette";
import { useLandingFacts } from "@/lib/landingFacts";
import { portalMeta, runSerial } from "@/lib/portals";

const CAPTIONS = [
  {
    title: "Set the search.",
    body: "Choose a portal and narrow by keyword, category, sector, organization, department, city or date; every filter mirrors the portal's own search.",
  },
  {
    title: "The run reads every page.",
    body: "A headless browser pages through every result, skipping tenders that close too soon. Each page read draws one ring; pause, resume or stop at any point.",
  },
  {
    title: "Take the workbook.",
    body: "Results land in the database and an Excel workbook named after your filters, with the run's full history kept to audit.",
  },
];

/**
 * "How a run works", printed as one record of the latest real run: what it
 * searched for, the rosette of the pages it read, and the serial it was issued
 * under, joined left to right with the explanations as captions beneath. With
 * no server to ask, the record keeps its captions and leaves the marks blank.
 */
export default function RunStrip() {
  const { latest } = useLandingFacts();
  const pages = latest?.total_pages ?? null;

  const marks = [
    <div key="search">
      <p className="font-mono text-[13px] text-ink-500">{latest ? `${portalMeta(latest.scraper).label} · search` : "search"}</p>
      <p className="mt-1 font-mono text-2xl font-bold tracking-tight text-ink-950">{latest ? latest.search || "all active tenders" : "—"}</p>
    </div>,
    <div key="pages" className="flex items-center gap-4">
      <Rosette read={pages ?? 0} total={pages} live={false} size={120} drawIn />
      <p className="font-mono text-2xl font-bold tracking-tight text-ink-950">
        {pages ? `${pages} of ${pages}` : "—"}
        <span className="block text-[13px] font-medium text-ink-500">pages read</span>
      </p>
    </div>,
    <div key="book">
      <p className="font-mono text-[13px] text-ink-500">issued as</p>
      <p className="mt-1 font-mono text-2xl font-bold tracking-tight text-ink-950">
        {latest ? runSerial(latest.scraper, latest.run_id) : "—"}
      </p>
      {latest && (
        <p className="mt-1 text-sm font-semibold text-intaglio-800">
          {latest.excel_exported ? "Excel ready" : "Saved to the database"}
        </p>
      )}
    </div>,
  ];

  return (
    <figure className="sheet-rule mt-10 rounded-md bg-sheet px-6 py-8 shadow-[0_1px_0_var(--color-ink-200),0_18px_40px_-28px_rgba(18,64,47,0.35)] sm:px-10 sm:py-10">
      <ol className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_3rem_minmax(0,1fr)_3rem_minmax(0,1fr)] lg:items-start lg:gap-0">
        {marks.map((mark, i) => (
          <Fragment key={i}>
            {i > 0 && (
              <li aria-hidden className="hidden h-[120px] items-center lg:flex lg:px-3">
                <span className="h-px flex-1 bg-ink-300" />
                <span className="h-1.5 w-1.5 rotate-45 border-r border-t border-ink-400" />
              </li>
            )}
            <li className={`border-l border-ink-200 pl-5 lg:border-l-0 ${i > 0 ? "lg:pl-4" : "lg:pl-0"}`}>
              <div className="flex min-h-[120px] items-center">{mark}</div>
              <p className="mt-5 max-w-[34ch] text-sm leading-relaxed text-ink-600">
                <span className="font-bold text-ink-900">{CAPTIONS[i].title}</span> {CAPTIONS[i].body}
              </p>
            </li>
          </Fragment>
        ))}
      </ol>
      <figcaption className="sr-only">The latest completed run, from its search to its workbook.</figcaption>
    </figure>
  );
}
