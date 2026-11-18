"use client";

import { useEffect, useState } from "react";
import { TableFilter } from "@/components/ui";
import { listPunjabBids, type PunjabBid } from "@/lib/api";
import { formatDay } from "@/lib/runs";

const PAGE_SIZE = 500;

/** The tenders a Punjab run has saved, streamed in as the scraper writes them. */
export default function PunjabResults({ runId }: { runId: string }) {
  const [bids, setBids] = useState<PunjabBid[]>([]);
  const [filterQuery, setFilterQuery] = useState("");

  useEffect(() => {
    let active = true;
    let lastId = 0;
    let busy = false;

    const poll = async () => {
      if (busy) return;
      busy = true;
      try {
        const fresh: PunjabBid[] = [];
        for (let page = 0; page < 50; page++) {
          const res = await listPunjabBids({ run_id: runId, after_id: lastId, limit: PAGE_SIZE });
          if (!active) return;
          const rows = res.bids ?? [];
          if (rows.length === 0) break;
          fresh.push(...rows);
          lastId = Math.max(lastId, ...rows.map((b) => b.id));
          if (rows.length < PAGE_SIZE) break;
        }
        if (fresh.length > 0) {
          setBids((prev) => {
            const existingIds = new Set(prev.map((b) => b.id));
            // Rows arrive oldest-first; the table shows newest on top.
            return [...fresh.filter((b) => !existingIds.has(b.id)).reverse(), ...prev];
          });
        }
      } catch {
        // A failed poll is retried on the next interval.
      } finally {
        busy = false;
      }
    };

    poll();
    const timer = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [runId]);

  const query = filterQuery.toLowerCase();
  const displayed = bids.filter(
    (b) =>
      !query ||
      b.title.toLowerCase().includes(query) ||
      b.tender_no.toLowerCase().includes(query) ||
      (b.department ?? "").toLowerCase().includes(query),
  );

  return (
    <section className="overflow-hidden rounded-xl border border-ink-200 bg-sheet shadow-sm shadow-ink-900/[0.03]">
      <div className="flex flex-col gap-3 border-b border-ink-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-[15px] text-ink-950">Live tender results <span className="font-mono text-ink-600">{bids.length.toLocaleString()}</span></h2>
          <p className="mt-0.5 text-xs text-ink-600">
            Live tenders from the Punjab e-Procurement portal, with their notice and bidding documents.
          </p>
        </div>

        <TableFilter value={filterQuery} onChange={setFilterQuery} label="Filter tender results" />
      </div>

      <div className="max-h-[70vh] overflow-auto">
        <table className="w-full text-left text-[13px]">
          <thead className="sticky top-0 z-[1] whitespace-nowrap border-b border-ink-200 bg-sheet text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-600">
            <tr>
              <th className="px-3 py-2">Tender ID</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Department</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Notice</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Closing</th>
              <th className="px-3 py-2">Documents</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100 bg-white/60 text-ink-800">
            {displayed.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-ink-500">
                  {bids.length > 0 ? `No rows match “${filterQuery}”.` : "No tenders saved for this run yet."}
                </td>
              </tr>
            ) : (
              displayed.map((b) => (
                <tr key={b.id} className="hover:bg-intaglio-50">
                  <td className="whitespace-nowrap px-3 py-2 font-mono font-medium text-ink-900">{b.tender_no}</td>
                  <td className="max-w-xs truncate px-3 py-2" title={b.title}>
                    {b.title}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-ink-600" title={b.department ?? undefined}>
                    {b.department || "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-ink-500">{b.procurement_type || "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-ink-500">{b.notice_type || "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {b.status ? (
                      <span className="inline-flex items-center rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-semibold text-amber-800 ring-1 ring-amber-200">
                        {b.status}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-ink-600">{formatDay(b.closing_on)}</td>
                  <td className="space-x-2 whitespace-nowrap px-3 py-2">
                    <PdfLink href={b.notice_url} label="Notice" />
                    <PdfLink href={b.document_url} label="Bidding" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** The server only stores links that match the site's PDF paths. */
function PdfLink({ href, label }: { href: string | null; label: string }) {
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noreferrer" className="font-medium text-ink-800 underline decoration-intaglio-300 underline-offset-2 hover:text-ink-950 hover:decoration-intaglio-800">
      {label}
    </a>
  );
}
