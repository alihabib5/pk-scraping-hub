import Link from "next/link";
import { Activity, ArrowRight, Database, FileSpreadsheet, Filter, Pause } from "lucide-react";

import Logo from "@/components/Logo";
import { apiDocsUrl } from "@/lib/api";

/**
 * The landing page's first screen: a navy hero with the nav on top of it.
 *
 * Adapted from a "Hero 14" layout (nav bar, badge, two-line heading with an
 * italic serif second line, one call to action, a row of marks at the foot).
 * Differences that make it PK-Hub's: the palette (navy ink with a gold glow in
 * place of a stock photo), the italic line set in the app's serif, the foot row
 * listing what a run gives you rather than partner logos, and an entrance
 * animation done in CSS so no animation library is added for one page.
 *
 * Server component: nothing here holds state.
 */

const NAV = [
  { label: "Sources", href: "#sources" },
  { label: "How it works", href: "#how-it-works" },
];

const FEATURES = [
  { label: "Every portal filter", Icon: Filter },
  { label: "Live progress", Icon: Activity },
  { label: "Pause & resume", Icon: Pause },
  { label: "Excel workbooks", Icon: FileSpreadsheet },
  { label: "Run history", Icon: Database },
];

/** Stagger step for the entrance animation, in milliseconds. */
const STEP = 140;
const rise = (n: number) => ({ "--d": `${200 + n * STEP}ms` }) as React.CSSProperties;

export default function LandingHero({
  brandName = "PK-Hub",
  badgeText = "Bid intelligence — Pakistan",
  headingLine1 = "Every public bid.",
  headingLine2 = "Found automatically.",
  description = "PK-Hub runs the PPRA tender searches you care about, collects every matching tender page by page, and hands you a spreadsheet, without anyone clicking through a government website.",
  primaryCtaLabel = "Open console",
  primaryCtaHref = "/console/ppra",
  secondaryCtaLabel = "View sources",
  secondaryCtaHref = "#sources",
  eyebrow = "What every run gives you",
}: {
  brandName?: string;
  badgeText?: string;
  headingLine1?: string;
  headingLine2?: string;
  description?: string;
  primaryCtaLabel?: string;
  primaryCtaHref?: string;
  secondaryCtaLabel?: string;
  secondaryCtaHref?: string;
  eyebrow?: string;
}) {
  return (
    <section className="relative isolate flex min-h-[680px] w-full overflow-hidden bg-ink-950 text-white md:min-h-[740px]">
      {/* Backdrop: a gold glow rising from the foot and a cool light at the top left. No image to load. */}
      <div
        aria-hidden
        className="hero-backdrop absolute inset-0 -z-10"
        style={{
          backgroundImage: [
            "radial-gradient(60rem 28rem at 50% 108%, rgba(185,135,60,0.32), transparent 70%)",
            "radial-gradient(44rem 26rem at 8% -6%, rgba(85,119,155,0.30), transparent 70%)",
            "linear-gradient(180deg, #061224 0%, #0b1f3a 100%)",
          ].join(", "),
        }}
      />
      {/* Fine ruled lines, faded toward the edges, for a ledger feel. */}
      <div
        aria-hidden
        className="absolute inset-0 -z-10 opacity-[0.07] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, #fff 0 1px, transparent 1px 44px), repeating-linear-gradient(90deg, #fff 0 1px, transparent 1px 44px)",
        }}
      />

      <div className="relative z-10 flex w-full flex-col">
        <nav
          aria-label="Primary"
          className="hero-rise mx-auto flex min-h-14 w-full max-w-6xl items-center justify-between border-b border-white/[0.07] px-6 py-3"
          style={rise(0)}
        >
          <Link href="/" className="inline-flex min-h-10 items-center gap-2.5 transition hover:opacity-85 active:scale-[0.97]">
            <Logo className="h-8 w-8 ring-1 ring-white/15" />
            <span className="text-base font-semibold tracking-tight">{brandName}</span>
          </Link>

          <div className="hidden items-center gap-9 md:flex">
            {NAV.map((l) => (
              <a key={l.label} href={l.href} className="inline-flex min-h-10 items-center text-sm text-white/80 transition hover:text-white">
                {l.label}
              </a>
            ))}
            <a
              href={apiDocsUrl()}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-10 items-center text-sm text-white/80 transition hover:text-white"
            >
              API docs
            </a>
          </div>

          <Link
            href={primaryCtaHref}
            className="group inline-flex min-h-10 items-center justify-center gap-1.5 rounded-full bg-white px-5 text-sm font-medium text-ink-900 shadow-sm transition hover:bg-gold-50 active:scale-[0.97]"
          >
            {primaryCtaLabel}
            <ArrowRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
          </Link>
        </nav>

        <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center px-6 pb-10 pt-16 text-center sm:pt-20">
          <div
            className="hero-rise inline-flex min-h-8 items-center gap-2 rounded-full bg-white/10 px-4 text-[11px] font-semibold uppercase tracking-widest text-white/80 ring-1 ring-inset ring-white/10 backdrop-blur-md"
            style={rise(1)}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-gold-400 shadow-[0_0_12px_rgba(210,165,92,0.8)]" />
            {badgeText}
          </div>

          <h1 className="hero-rise mt-6 max-w-4xl text-balance text-[clamp(2.6rem,6vw,5.4rem)] font-light leading-[1] tracking-tight" style={rise(2)}>
            <span className="block">{headingLine1}</span>
            <span className="mt-1 block font-serif text-[1.1em] font-normal italic leading-[0.95] text-gold-300">{headingLine2}</span>
          </h1>

          <p className="hero-rise mt-6 max-w-xl text-pretty text-[15px] leading-7 text-white/70" style={rise(3)}>
            {description}
          </p>

          <div className="hero-rise mt-8 flex flex-wrap items-center justify-center gap-3" style={rise(4)}>
            <Link
              href={primaryCtaHref}
              className="group inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg bg-white px-6 text-sm font-medium text-ink-900 shadow-sm transition hover:bg-gold-50 active:scale-[0.97]"
            >
              {primaryCtaLabel}
              <ArrowRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
            </Link>
            <a
              href={secondaryCtaHref}
              className="inline-flex min-h-11 items-center justify-center rounded-lg px-6 text-sm font-medium text-white ring-1 ring-inset ring-white/25 transition hover:bg-white/10 active:scale-[0.97]"
            >
              {secondaryCtaLabel}
            </a>
          </div>

          <div className="hero-rise mt-auto w-full pb-6 pt-16" style={rise(5)}>
            <p className="text-sm font-light text-white/60">{eyebrow}</p>
            <ul className="mx-auto mt-3 flex max-w-3xl flex-wrap items-center justify-center gap-x-9 gap-y-4">
              {FEATURES.map(({ label, Icon }) => (
                <li key={label} className="flex items-center gap-2.5 text-white/85">
                  <Icon className="h-4 w-4 text-gold-400" aria-hidden />
                  <span className="text-base font-medium tracking-tight">{label}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
