"use client";

import { useEffect, useState } from "react";
import { TableFilter } from "@/components/ui";
import { listPpraBids, type PpraBid } from "@/lib/api";
import { formatDay } from "@/lib/runs";

const PAGE_SIZE = 500;

/** The tenders a run has saved, streamed in as the scraper writes them. */
export default function PpraResults({ runId }: { runId: string }) {
  const [bids, setBids] = useState<PpraBid[]>([]);
  const [filterQuery, setFilterQuery] = useState("");

  useEffect(() => {
    let active = true;
    let lastId = 0;
    let busy = false;

    const poll = async () => {
      // A large run can take longer than one interval to page through.
      if (busy) return;
      busy = true;
      try {
        const fresh: PpraBid[] = [];
        // Page forward from the cursor until caught up, so reopening a finished
        // run with thousands of rows loads all of them, not just one page.
        for (let page = 0; page < 50; page++) {
          const res = await listPpraBids({ run_id: runId, after_id: lastId, limit: PAGE_SIZE });
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
            const newBids = fresh.filter((b) => !existingIds.has(b.id)).reverse();
            return [...newBids, ...prev];
          });
        }
      } catch {
        // Silently tolerate transient polling error
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

  const displayed = bids.filter((b) => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    return (
      (b.title || "").toLowerCase().includes(q) ||
      (b.tender_no || "").toLowerCase().includes(q) ||
      (b.organization || "").toLowerCase().includes(q) ||
      (b.city || "").toLowerCase().includes(q)
    );
  });

  return (
    <section className="overflow-hidden rounded-xl border border-ink-200 bg-sheet shadow-sm shadow-ink-900/[0.03]">
      <div className="flex flex-col gap-3 border-b border-ink-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-[15px] text-ink-950">
            Live tender results <span className="font-mono text-ink-600">{bids.length.toLocaleString()}</span>
          </h2>
          <p className="mt-0.5 text-xs text-ink-600">
            Real-time feed of active federal tenders and corrigendums from PPRA.
          </p>
        </div>

        <TableFilter value={filterQuery} onChange={setFilterQuery} label="Filter tender results" />
      </div>

      <div className="max-h-[70vh] overflow-auto">
        <table className="w-full text-left text-[13px]">
          <thead className="sticky top-0 z-[1] whitespace-nowrap border-b border-ink-200 bg-sheet text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-600">
            <tr>
              <th className="px-3 py-2">Tender No</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Organization</th>
              <th className="px-3 py-2">Sector</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Closing (PKT)</th>
              <th className="px-3 py-2">Link</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100 bg-white/60 text-ink-800">
            {displayed.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-ink-500">
                  {bids.length > 0 ? `No rows match “${filterQuery}”.` : "No tenders saved for this run yet."}
                </td>
              </tr>
            ) : (
              displayed.map((b) => (
                <tr key={b.id} className="hover:bg-intaglio-50">
                  <td className="whitespace-nowrap px-3 py-2 font-mono font-medium text-ink-900">
                    {b.tender_no}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2" title={b.title}>
                    {b.title}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-ink-600" title={b.organization ?? undefined}>
                    {b.organization || "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-ink-500">
                    {b.sector || "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold ${
                        b.status?.toLowerCase().includes("corrigendum")
                          ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                          : b.status?.toLowerCase().includes("cancelled")
                          ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
                          : "bg-intaglio-50 text-intaglio-900 ring-1 ring-intaglio-200"
                      }`}
                    >
                      {b.status || "Published"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-ink-600">
                    {formatDay(b.closing_at)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {b.detail_url ? (
                      <a
                        href={b.detail_url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium text-ink-800 underline decoration-intaglio-300 underline-offset-2 hover:text-ink-950 hover:decoration-intaglio-800"
                      >
                        View
                      </a>
                    ) : (
                      "—"
                    )}
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

