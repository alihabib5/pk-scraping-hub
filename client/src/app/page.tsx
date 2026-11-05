import Link from "next/link";
import { ArrowRight, Database, Moon } from "lucide-react";

import LandingHero from "@/components/LandingHero";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#faf8f5] flex flex-col justify-between">
      <LandingHero />

      <main className="max-w-6xl mx-auto px-6 py-16 w-full flex-1">
        {/* Portal Source Card Section */}
        <section id="sources" className="mb-24">
          <div className="mb-8">
            <h2 className="font-serif text-3xl font-normal text-[#0f1f38] mb-2">
              2 Pakistani portals, one console.
            </h2>
            <p className="text-xs md:text-sm text-zinc-500 max-w-2xl">
              Federal and Punjab search filters, paging and closing dates, behind one interface.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
          <div className="bg-white border border-[#e8e4dc] rounded-2xl p-8 shadow-xs hover:border-zinc-300 transition-colors">
            <div className="flex items-center justify-between mb-5">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 ring-1 ring-emerald-200/80 text-emerald-700 flex items-center justify-center">
                <Moon className="w-5 h-5 fill-emerald-600/20 text-emerald-700" />
              </div>
              <Link
                href="/console/ppra"
                aria-label="Open the PPRA Pakistan console"
                className="-m-2.5 flex h-10 w-10 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-50 hover:text-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#b47834]"
              >
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <h3 className="font-serif text-2xl font-normal text-[#0f1f38] mb-1">
              PPRA Pakistan
            </h3>
            <div className="text-xs text-zinc-400 mb-4">
              Public Procurement Regulatory Authority
            </div>

            <p className="text-xs md:text-sm text-zinc-600 leading-relaxed mb-6">
              Automate public tender discovery across Pakistan's federal e-Procurement system (EPMS), filter by organization, sector, category and closing date, and export all matching active notices into structured Excel workbooks.
            </p>

            <div className="flex flex-wrap gap-2 mb-8">
              {[
                "Tender & Corrigendum grid",
                "Multi-filter discovery",
                "Live table tracking",
                "Excel workbook",
              ].map((badge) => (
                <span
                  key={badge}
                  className="px-3 py-1 rounded-full text-[11px] font-medium bg-[#f0f6fa] text-[#245275] border border-[#dce8f0]"
                >
                  {badge}
                </span>
              ))}
            </div>

            <div className="text-xs font-mono text-zinc-400">
              epms.ppra.gov.pk
            </div>
          </div>

          <div className="bg-white border border-[#e8e4dc] rounded-2xl p-8 shadow-xs hover:border-zinc-300 transition-colors">
            <div className="flex items-center justify-between mb-5">
              <div className="w-10 h-10 rounded-xl bg-sky-50 ring-1 ring-sky-200/80 text-sky-700 flex items-center justify-center">
                <Moon className="w-5 h-5 fill-sky-600/20 text-sky-700" />
              </div>
              <Link
                href="/console/punjab"
                aria-label="Open the PPRA Punjab console"
                className="-m-2.5 flex h-10 w-10 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-50 hover:text-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#b47834]"
              >
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <h3 className="font-serif text-2xl font-normal text-[#0f1f38] mb-1">
              PPRA Punjab
            </h3>
            <div className="text-xs text-zinc-400 mb-4">
              Punjab Procurement Regulatory Authority
            </div>

            <p className="text-xs md:text-sm text-zinc-600 leading-relaxed mb-6">
              Collect live tenders from the Punjab e-Procurement portal, filter by type, category, department and closing date, leave out auctions, and export every match with its PDF links into structured Excel workbooks.
            </p>

            <div className="flex flex-wrap gap-2 mb-8">
              {[
                "Auctions excluded",
                "Notice & bidding PDFs",
                "Live table tracking",
                "Excel workbook",
              ].map((badge) => (
                <span
                  key={badge}
                  className="px-3 py-1 rounded-full text-[11px] font-medium bg-[#f0f6fa] text-[#245275] border border-[#dce8f0]"
                >
                  {badge}
                </span>
              ))}
            </div>

            <div className="text-xs font-mono text-zinc-400">
              eproc.punjab.gov.pk
            </div>
          </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how-it-works" className="mb-24 pt-8 border-t border-[#e8e4dc]">
          <div className="flex items-center gap-2 mb-4">
            <span className="w-4 h-[1.5px] bg-[#b47834]" />
            <span className="text-[11px] font-bold tracking-widest text-[#b47834] uppercase">
              HOW IT WORKS
            </span>
          </div>

          <h2 className="font-serif text-3xl font-normal text-[#0f1f38] mb-12">
            Set the scope. Walk away.
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="border-t border-[#e8e4dc] pt-6">
              <div className="font-serif text-sm font-medium text-[#b47834] mb-3">01</div>
              <h3 className="font-serif text-lg text-[#0f1f38] mb-2 font-normal">
                Choose a source and scope
              </h3>
              <p className="text-xs text-zinc-600 leading-relaxed">
                Narrow by keyword, category, sector, organization, city or advertise date. Every filter mirrors the portal's own search.
              </p>
            </div>

            <div className="border-t border-[#e8e4dc] pt-6">
              <div className="font-serif text-sm font-medium text-[#b47834] mb-3">02</div>
              <h3 className="font-serif text-lg text-[#0f1f38] mb-2 font-normal">
                The crawler does the reading
              </h3>
              <p className="text-xs text-zinc-600 leading-relaxed">
                A headless browser runs the search on epms.ppra.gov.pk and pages through every result, skipping tenders that close too soon.
              </p>
            </div>

            <div className="border-t border-[#e8e4dc] pt-6">
              <div className="font-serif text-sm font-medium text-[#b47834] mb-3">03</div>
              <h3 className="font-serif text-lg text-[#0f1f38] mb-2 font-normal">
                Take away a spreadsheet
              </h3>
              <p className="text-xs text-zinc-600 leading-relaxed">
                Results land in the database and an Excel workbook named after your filters — with the run's full history kept so you can audit what happened.
              </p>
            </div>
          </div>
        </section>

        {/* Midnight Callout Banner */}
        <section className="bg-[#0f1f38] rounded-3xl p-12 md:p-16 text-center text-white shadow-md">
          <h2 className="font-serif text-3xl md:text-4xl font-normal mb-4">
            Stop reading procurement portals.
          </h2>
          <p className="text-xs md:text-sm text-zinc-300 max-w-xl mx-auto mb-8 leading-relaxed">
            Pick a source, choose your keywords, and let the crawler bring the work back to you.
          </p>
          <Link
            href="/console/ppra"
            className="inline-flex min-h-11 items-center gap-2 px-6 py-2.5 rounded-lg bg-white hover:bg-zinc-100 text-[#0f1f38] text-xs font-semibold transition-colors"
          >
            Open console <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#e8e4dc] bg-white py-8 px-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-xs text-zinc-500">
          <div className="flex items-center gap-2 font-semibold text-[#0f1f38]">
            <div className="w-5 h-5 rounded bg-[#0f1f38] flex items-center justify-center text-white text-[10px]">
              <Database className="w-3 h-3" />
            </div>
            Scraping Hub
          </div>
          <div>Automated bid collection for public procurement portals.</div>
        </div>
      </footer>
    </div>
  );
}
