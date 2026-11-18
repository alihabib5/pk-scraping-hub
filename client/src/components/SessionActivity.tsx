"use client";

import { useEffect, useRef, useState } from "react";

import { isRunActive, type Portal } from "@/lib/api";
import { useSession } from "@/lib/sessions";

/**
 * The run's log, streaming, inside the portal's own panel.
 *
 * The tail was only ever reachable from the footer bar or the Live preview
 * modal, which meant the one place you could not watch a scrape was the page
 * that launched it. It is buffered in the session registry now, by the engine,
 * so this reads rather than fetches — and because the buffer belongs to the
 * slot and not to this component, the lines that arrived while you were looking
 * at another portal are all here when you come back.
 */
export default function SessionActivity({ portal }: { portal: Portal }) {
  const session = useSession(portal);
  const [open, setOpen] = useState(true);
  const box = useRef<HTMLPreElement>(null);
  const lines = session?.logs ?? [];
  const live = !!session?.run && isRunActive(session.run);

  // Follow the tail, but only while it is already at the bottom — scrolling up
  // to read something is not an invitation to be yanked back down.
  useEffect(() => {
    const el = box.current;
    if (!el || !open) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (atBottom) el.scrollTo({ top: el.scrollHeight });
  }, [lines, open]);

  if (!session?.runId) return null;

  return (
    <section className="overflow-hidden rounded-xl border border-ink-200 bg-sheet shadow-sm shadow-ink-900/[0.03]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-100 px-5 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          {live ? (
            <span className="relative flex h-2 w-2 shrink-0" aria-hidden>
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-serial-600/60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-serial-600" />
            </span>
          ) : (
            <span className="h-2 w-2 shrink-0 rounded-full bg-ink-300" aria-hidden />
          )}
          <h2 className="font-display text-[15px] text-ink-950">Live activity</h2>
          <span className="font-mono text-xs text-ink-600">
            {lines.length > 0
              ? `${lines.length}${lines.length === 500 ? "+" : ""} line${lines.length === 1 ? "" : "s"}`
              : live
                ? "waiting for output…"
                : "no output"}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="rounded-md px-2 py-1 text-xs font-medium text-ink-500 transition hover:bg-ink-50 hover:text-ink-900"
        >
          {open ? "Hide" : "Show"}
        </button>
      </header>

      {open && (
        <pre
          ref={box}
          // aria-live but not assertive: a screen reader should be able to hear
          // the tail on request, not have every scraped row read at it.
          aria-live="polite"
          aria-label={`${portal} run log`}
          className="max-h-64 overflow-y-auto bg-intaglio-950 px-4 py-3 font-mono text-[11.5px] leading-relaxed text-intaglio-100"
        >
          {lines.length === 0
            ? live
              ? "waiting for output…"
              : "This run produced no log output."
            : lines.map((line) => `${line.level.padEnd(7)} ${line.message}`).join("\n")}
        </pre>
      )}
    </section>
  );
}
