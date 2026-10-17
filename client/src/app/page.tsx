import Link from "next/link";
import { ArrowRight, Database, Moon } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#faf8f5] flex flex-col justify-between">
      {/* Top Navbar */}
      <header className="bg-white border-b border-[#e8e4dc] sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#0f1f38] flex items-center justify-center text-white shadow-xs">
                <Database className="w-4 h-4" />
              </div>
              <span className="font-semibold text-base text-[#0f1f38] tracking-tight">
                Scraping Hub
              </span>
            </Link>


            <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-zinc-600">
              <a href="#sources" className="hover:text-zinc-900 transition-colors">Sources</a>
              <a href="#how-it-works" className="hover:text-zinc-900 transition-colors">How it works</a>
            </nav>
          </div>

          <Link
            href="/console/ppra"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0f1f38] hover:bg-[#162a4d] text-white text-xs font-medium transition-colors shadow-xs"
          >
            Open console <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-6xl mx-auto px-6 py-16 w-full flex-1">
        <div className="mb-20">
          <div className="flex items-center gap-2 mb-6">
            <span className="w-5 h-[1.5px] bg-[#b47834]" />
            <span className="text-[11px] font-bold tracking-widest text-[#b47834] uppercase">
              BID INTELLIGENCE — PAKISTAN
            </span>
          </div>

          <h1 className="font-serif text-5xl md:text-6xl font-normal tracking-tight text-[#0f1f38] leading-[1.1] mb-2">
            Every public bid.
          </h1>
          <h2 className="font-serif text-5xl md:text-6xl font-normal tracking-tight text-[#536f88] leading-[1.1] mb-8">
            Found automatically.
          </h2>

          <p className="text-sm md:text-base text-zinc-600 max-w-2xl leading-relaxed mb-8">
            Scraping Hub runs the PPRA tender searches you care about, collects every matching tender page by page, and hands you a spreadsheet — without anyone clicking through a government website.
          </p>

          <div className="flex items-center gap-3">
            <Link
              href="/console/ppra"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#0f1f38] hover:bg-[#162a4d] text-white text-xs font-medium transition-colors shadow-xs"
            >
              Open console <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <a
              href="#sources"
              className="inline-flex items-center px-5 py-2.5 rounded-lg bg-white border border-[#e8e4dc] hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition-colors shadow-xs"
            >
              View sources
            </a>
          </div>
        </div>

        {/* Portal Source Card Section */}
        <section id="sources" className="mb-24">
          <div className="mb-8">
            <h2 className="font-serif text-3xl font-normal text-[#0f1f38] mb-2">
              1 Pakistani portal, one console.
            </h2>
            <p className="text-xs md:text-sm text-zinc-500 max-w-2xl">
              PPRA's search filters, paging and closing dates, behind one interface.
            </p>
          </div>

          <div className="max-w-2xl bg-white border border-[#e8e4dc] rounded-2xl p-8 shadow-xs hover:border-zinc-300 transition-colors">
            <div className="flex items-center justify-between mb-5">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 ring-1 ring-emerald-200/80 text-emerald-700 flex items-center justify-center">
                <Moon className="w-5 h-5 fill-emerald-600/20 text-emerald-700" />
              </div>
              <Link href="/console/ppra" className="text-zinc-400 hover:text-zinc-700">
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
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-white hover:bg-zinc-100 text-[#0f1f38] text-xs font-semibold transition-colors"
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
