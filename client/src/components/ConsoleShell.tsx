"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import ActiveJobs from "@/components/ActiveJobs";
import Logo from "@/components/Logo";
import PortalPanelHost from "@/components/PortalPanelHost";
import SessionEngine from "@/components/SessionEngine";
import { LinkButton } from "@/components/ui";
import { apiDocsUrl, isRunActive, type Portal } from "@/lib/api";
import { isPortal, PORTALS, pluralize, runSerialShort } from "@/lib/portals";
import { useJobsFeed, useSlots } from "@/lib/sessions";

const SECTIONS = [
  { key: "", label: "Console" },
  { key: "history", label: "History" },
  { key: "exports", label: "Downloads" },
] as const;

/**
 * Chrome for every console route: the intaglio portal rail, the section bar,
 * and the cross-portal jobs bar.
 *
 * Both nav dimensions live in the URL (`/console/{portal}/{section}`), so the
 * shell derives its active state from the pathname rather than holding any.
 *
 * It also owns the two things that must outlive a page. `SessionEngine` watches
 * every run on every portal for as long as the console is open, and
 * `PortalPanelHost` keeps the portal panels themselves mounted across
 * navigation. Both live here because a layout survives the routes under it —
 * which is exactly what a scrape in flight needs and a page cannot give it.
 */
export default function ConsoleShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean); // ["console", portal, section?]
  const portal = (segments[1] ?? "") as Portal;
  const section = segments[2] ?? "";

  // The run in flight on each portal, so the rail can show its serial while
  // you are looking at another portal: a run you navigated away from is still
  // going, and the serial is how you recognise it.
  const slots = useSlots();
  const liveRun = (p: Portal) => {
    const run = slots[p]?.run;
    return run && isRunActive(run) ? run : null;
  };
  const { capacity } = useJobsFeed();

  const href = (p: string, s: string) => `/console/${p}${s ? `/${s}` : ""}`;

  return (
    <div className="flex min-h-screen">
      {/* Portal rail */}
      <aside data-surface="dark" className="sticky top-0 hidden h-screen w-62 shrink-0 flex-col bg-intaglio-900 text-intaglio-100 lg:flex">
        <span aria-hidden className="engraved-edge absolute inset-y-0 right-0 w-1.5" />
        <Link href="/" title="PK-Hub home" className="flex items-center gap-2.5 px-5 pb-7 pt-5">
          <Logo />
          <span className="text-[17px] font-bold tracking-tight text-white">PK-Hub</span>
        </Link>

        <nav aria-label="Portals" className="flex-1">
          <p className="px-5 pb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-intaglio-300">Portals</p>
          <ul className="space-y-0.5 px-3">
            {PORTALS.map((p) => {
              const isActive = p.key === portal;
              const run = liveRun(p.key);
              return (
                <li key={p.key}>
                  <Link
                    href={href(p.key, section)}
                    aria-current={isActive ? "page" : undefined}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition ${
                      isActive
                        ? "bg-intaglio-950 shadow-[inset_3px_0_0_var(--color-ochre-400)]"
                        : "hover:bg-intaglio-800"
                    }`}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-white">{p.label}</span>
                      <span className="block truncate text-xs text-intaglio-300">{p.tagline}</span>
                    </span>
                    {run && (
                      <span
                        className="shrink-0 rounded-full bg-serial-600 px-2 py-0.5 font-mono text-[11px] font-bold text-white"
                        title="Run in flight"
                      >
                        {runSerialShort(p.key, run.run_id)}
                        <span className="sr-only"> run in flight</span>
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <p className="border-t border-intaglio-800 px-5 py-4 text-xs text-intaglio-300">
          {capacity
            ? `${pluralize(capacity.running + capacity.paused, "run", "runs")} in flight · ${Math.max(
                0,
                capacity.capacity - capacity.running - capacity.paused,
              )} of ${capacity.capacity} slots free`
            : pluralize(PORTALS.length, "portal", "portals")}
        </p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-ink-200 bg-sheet/95 backdrop-blur">
          <div className="flex h-15 items-center gap-5 px-4 sm:gap-6 sm:px-8">
            <nav className="no-scrollbar flex min-w-0 flex-1 items-stretch gap-6 self-stretch overflow-x-auto" aria-label="Sections">
              {SECTIONS.map((s) => {
                const isActive = s.key === section;
                return (
                  <Link
                    key={s.key || "console"}
                    href={href(portal, s.key)}
                    aria-current={isActive ? "page" : undefined}
                    className={`flex shrink-0 items-center text-sm transition ${
                      isActive
                        ? "font-bold text-ink-950 shadow-[inset_0_-2px_0_var(--color-intaglio-900)]"
                        : "font-medium text-ink-600 hover:text-ink-950"
                    }`}
                  >
                    {s.label}
                  </Link>
                );
              })}
            </nav>
            <LinkButton href={apiDocsUrl()} target="_blank" rel="noopener noreferrer" size="sm">
              API docs
            </LinkButton>
          </div>

          {/* Portal switcher for narrow screens: the rail's job, on one line. */}
          <div data-surface="dark" className="flex items-center gap-3 bg-intaglio-900 py-2.5 pl-4 sm:pl-8 lg:hidden">
          <Link href="/" title="PK-Hub home" className="flex shrink-0 items-center gap-2">
            <Logo className="h-7 w-7" />
            <span className="text-[15px] font-bold tracking-tight text-white">PK-Hub</span>
          </Link>
          <nav
            className="no-scrollbar flex min-w-0 flex-1 gap-2 overflow-x-auto pr-4 sm:pr-8"
            aria-label="Portals"
          >
            {PORTALS.map((p) => {
              const isActive = p.key === portal;
              const run = liveRun(p.key);
              return (
                <Link
                  key={p.key}
                  href={href(p.key, section)}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex min-h-9 shrink-0 items-center gap-2 rounded-full px-3.5 text-sm font-semibold transition ${
                    isActive ? "bg-sheet text-intaglio-900" : "text-intaglio-100 hover:bg-intaglio-800"
                  }`}
                >
                  {p.label}
                  {run && (
                    <span className="rounded-full bg-serial-600 px-1.5 font-mono text-[10px] font-bold text-white">
                      {runSerialShort(p.key, run.run_id)}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
          </div>
        </header>

        {/* Watches every run on every portal, independent of what is mounted. */}
        <SessionEngine />

        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-8 sm:py-8">
          {/* The portal panels are rendered here, by the layout, rather than
              by `[portal]/page.tsx` — that page renders nothing. A page is
              torn down on navigation; this is not, which is what lets a
              running scrape keep its view. The section pages (History,
              Downloads) still come through as children. */}
          <PortalPanelHost visible={section === "" && isPortal(portal)} portal={portal} />
          {children}
        </main>

        {/* Every in-flight scrape, on every portal. Lives in the shell, not
            on a page, so moving between portals never loses sight of a run —
            the run belongs to the server, not to the page that started it. */}
        <ActiveJobs />
      </div>
    </div>
  );
}
