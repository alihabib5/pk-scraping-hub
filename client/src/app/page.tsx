import { ArrowRight } from "lucide-react";
import Link from "next/link";

import IssueSheet from "@/components/IssueSheet";
import Logo from "@/components/Logo";
import RunStrip from "@/components/RunStrip";
import { apiDocsUrl } from "@/lib/api";
import { PORTALS } from "@/lib/portals";

const NAV = [
  { label: "Portals", href: "#portals" },
  { label: "How a run works", href: "#how" },
];

const HOSTS: Record<string, string> = { ppra: "epms.ppra.gov.pk", punjab: "eproc.punjab.gov.pk" };

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-stamp">
      <header data-surface="dark" className="relative bg-intaglio-900 text-white">
        <span aria-hidden className="absolute inset-x-0 bottom-0 h-1 [background-image:repeating-linear-gradient(90deg,var(--color-intaglio-700)_0_1px,transparent_1px_3px)]" />
        <div className="mx-auto flex min-h-16 w-full max-w-[1312px] flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-8 xl:px-16">
          <Link href="/" className="flex items-center gap-2.5">
            <Logo />
            <span className="text-lg font-bold tracking-tight">PK-Hub</span>
          </Link>
          <nav aria-label="Primary" className="hidden items-center gap-7 text-[15px] font-medium text-intaglio-200 md:flex">
            {NAV.map((l) => (
              <a key={l.href} href={l.href} className="transition hover:text-white">
                {l.label}
              </a>
            ))}
            <a href={apiDocsUrl()} target="_blank" rel="noreferrer" className="transition hover:text-white">
              API docs
            </a>
          </nav>
          <Link
            href="/console/ppra"
            className="ml-auto inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-white px-4 text-sm font-bold text-intaglio-900 transition hover:bg-intaglio-50"
          >
            Open console <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <IssueSheet />

        <section id="how" aria-labelledby="how-title" className="scroll-mt-6 border-t border-ink-200 bg-sheet">
          <div className="mx-auto w-full max-w-[1312px] px-4 py-16 sm:px-8 xl:px-16">
            <h2 id="how-title" className="font-display text-3xl tracking-tight text-intaglio-950">
              How a run works
            </h2>
            <RunStrip />
          </div>
        </section>

        <section id="portals" aria-labelledby="portals-title" className="scroll-mt-6 border-t border-ink-200">
          <div className="mx-auto w-full max-w-[1312px] px-4 py-16 sm:px-8 xl:px-16">
            <h2 id="portals-title" className="font-display text-3xl tracking-tight text-intaglio-950">
              Two Pakistani portals, one console
            </h2>
            <ul className="mt-8 divide-y divide-ink-200 border-y border-ink-200">
              {PORTALS.map((p) => (
                <li key={p.key} className="grid gap-x-10 gap-y-3 py-8 md:grid-cols-[240px_minmax(0,1fr)_auto] md:items-start">
                  <div>
                    <p className="font-mono text-sm font-bold tracking-wide text-ink-500">{p.code}</p>
                    <h3 className="mt-1 text-2xl font-bold tracking-tight text-ink-950">{p.label}</h3>
                    <p className="mt-0.5 font-mono text-[13px] text-ink-600">{HOSTS[p.key]}</p>
                  </div>
                  <p className="max-w-[62ch] text-[15px] leading-relaxed text-ink-700">{p.description}</p>
                  <Link
                    href={`/console/${p.key}`}
                    className="inline-flex min-h-11 items-center gap-1.5 justify-self-start rounded-lg bg-white px-4 text-sm font-bold text-intaglio-900 ring-1 ring-ink-200 transition hover:ring-intaglio-700 md:justify-self-end"
                  >
                    Open {p.label} <ArrowRight className="h-4 w-4" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section data-surface="dark" className="bg-intaglio-900 text-white">
          <div className="mx-auto flex w-full max-w-[1312px] flex-wrap items-center justify-between gap-6 px-4 py-14 sm:px-8 xl:px-16">
            <div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Stop reading procurement portals.</h2>
              <p className="mt-2 max-w-xl text-[15px] text-intaglio-200">
                Pick a source, choose your keywords, and let the crawler bring the work back to you.
              </p>
            </div>
            <Link
              href="/console/ppra"
              className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-white px-6 text-base font-bold text-intaglio-900 transition hover:bg-intaglio-50"
            >
              Open console <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink-200 bg-sheet">
        <div className="mx-auto flex w-full max-w-[1312px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-6 text-sm text-ink-600 sm:px-8 xl:px-16">
          <span className="flex items-center gap-2 font-bold text-ink-950">
            <Logo className="h-6 w-6" />
            PK-Hub
          </span>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-1">
            {NAV.map((l) => (
              <a key={l.href} href={l.href} className="underline-offset-4 hover:text-ink-950 hover:underline">
                {l.label}
              </a>
            ))}
            <a href={apiDocsUrl()} target="_blank" rel="noreferrer" className="underline-offset-4 hover:text-ink-950 hover:underline">
              API docs
            </a>
          </nav>
          <span className="basis-full text-ink-500 sm:basis-auto">Automated bid collection for Pakistan&apos;s public procurement portals.</span>
        </div>
      </footer>
    </div>
  );
}
