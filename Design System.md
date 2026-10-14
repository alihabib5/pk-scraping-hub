# PK-Hub — Editorial Modern Design System

> Refined styling specification based on the Scraping Hub editorial aesthetic: warm cream backgrounds, serif editorial typography, high-contrast navy hero cards, light-themed left sidebar with badge indicators, pill navigation toggles, and clean bordered forms.

---

## 1. Visual Identity & Aesthetic Principles

PK-Hub pairs high-density data management with a crisp, classic editorial publication feel:
- **Warm Canvas**: Ivory/cream wash (`bg-[#faf8f5]` / `bg-[#fcfbf9]`) paired with crisp white card containers (`bg-white`).
- **Typography Pairing**:
  - **Headings & Display**: Editorial Serif (`font-serif` / Georgia / Playfair / Newsreader style) for high-impact headlines and section titles.
  - **Body & UI**: Clean sans-serif (`font-sans` / Inter / system-ui) for form controls, labels, and metadata.
  - **Mono**: Monospace (`font-mono`) for portal domains, dates, and run IDs.
- **Deep Navy & Emerald Accents**:
  - Deep Midnight Navy (`#0f1e36` / `bg-[#0d1b2e]`) for hero callout blocks, primary headers, and CTAs.
  - Subdued Pakistani Emerald (`#059669` / `bg-emerald-50 text-emerald-800 ring-emerald-200`) for portal emblems, badges, and status indicators.
  - Warm Ochre / Gold (`text-[#b47834]`) for subtle eyebrow category labels (`HOW IT WORKS`, `BID INTELLIGENCE — PAKISTAN`).

---

## 2. Color Palette

### 2.1 Surfaces & Canvas
| Element | Tailwind Class | Hex / Value | Notes |
|---------|----------------|-------------|-------|
| Main Page Wash | `bg-[#faf8f5]` | `#faf8f5` | Warm cream background for landing and content |
| Card Container | `bg-white border border-[#e8e4dc]` | `#ffffff` | Clean white surface with warm neutral hairline border |
| Light Sidebar | `bg-[#fbfaf8] border-r border-[#e8e4dc]` | `#fbfaf8` | Low-contrast light sidebar |
| Dark Banner / Hero | `bg-[#0f1f38]` | `#0f1f38` | Rounded 2xl dark midnight banner for CTAs |
| Top Navbar | `bg-white border-b border-[#e8e4dc]` | `#ffffff` | Persistent white header |

### 2.2 Text Hierarchy
| Level | Class | Visual |
|-------|-------|--------|
| Hero Title | `font-serif text-5xl md:text-6xl font-semibold tracking-tight text-[#0f1f38]` | "Every public bid. Found automatically." |
| Section Title | `font-serif text-3xl font-normal text-[#0f1f38]` | "Set the scope. Walk away." |
| Card Title | `font-serif text-2xl font-semibold text-[#0f1f38]` | "PPRA Pakistan" |
| Eyebrow Label | `text-[11px] font-semibold tracking-widest uppercase text-[#b47834]` | "BID INTELLIGENCE — PAKISTAN" |
| Step Number | `font-serif text-sm font-medium text-[#b47834]` | "01", "02", "03" |
| Body Text | `text-sm text-zinc-600 leading-relaxed` | Descriptions and help text |
| Muted / Caption | `text-xs text-zinc-400` | Subtitle text and domain links |

### 2.3 Brand & Semantic Badges
| Badge Type | Appearance |
|------------|------------|
| Portal Emblem | `w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 flex items-center justify-center` |
| Filter Feature Pill | `text-xs px-2.5 py-1 rounded-full bg-sky-50/70 text-sky-800 border border-sky-100 font-medium` |
| Region Toggle (Pill) | Rounded-full pill container (`bg-zinc-100 p-1 border border-zinc-200`) with active white button (`bg-white shadow-xs text-zinc-900`) |

---

## 3. Key Components

### 3.1 Top Navigation Bar
- **Logo**: Dark square icon with white stacked disk symbol + "Scraping Hub" / "PK-Hub" in bold sans-serif.
- **Center Toggles**:
  - Segmented control for regions: `[ us US Portals ] [ PK Pakistan Portals ]`.
  - Text navigation links: `Sources`, `How it works`.
- **Right CTA**: Dark pill button (`bg-[#0f1f38] text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-[#162a4d]`).

### 3.2 Hero Header Section
- **Eyebrow**: Ochre horizontal line with text `— BID INTELLIGENCE — PAKISTAN`.
- **Headline**: Two-tone serif display headline:
  - Top line: `text-[#0f1f38]`
  - Bottom line: `text-[#536f88]` (muted dusty steel blue).
- **CTA Group**: Dual buttons:
  - Primary: `Open console →` (dark navy filled).
  - Secondary: `View sources` (white button with border).

### 3.3 Portal Discovery Card (PPRA)
```tsx
<div className="bg-white border border-[#e8e4dc] rounded-2xl p-7 shadow-xs">
  <div className="flex items-center justify-between mb-4">
    <div className="w-10 h-10 rounded-xl bg-emerald-50 ring-1 ring-emerald-200/80 text-emerald-700 flex items-center justify-center">
      {/* Crescent Icon */}
    </div>
    <span className="text-zinc-400 hover:text-zinc-700">→</span>
  </div>
  <h3 className="font-serif text-2xl font-medium text-[#0f1f38]">PPRA Pakistan</h3>
  <p className="text-xs text-zinc-500 mb-3">Public Procurement Regulatory Authority</p>
  <p className="text-sm text-zinc-600 mb-5 leading-relaxed">
    Automate public tender discovery across Pakistan's federal e-Procurement system (EPMS),
    filter by organization, sector, category and closing date, and export all matching active notices into structured Excel workbooks.
  </p>
  {/* Feature Pills */}
  <div className="flex flex-wrap gap-2 mb-6">
    <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#f0f6fa] text-[#245275] border border-[#dce8f0]">
      Tender & Corrigendum grid
    </span>
    <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#f0f6fa] text-[#245275] border border-[#dce8f0]">
      Multi-filter discovery
    </span>
    <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#f0f6fa] text-[#245275] border border-[#dce8f0]">
      Live table tracking
    </span>
    <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#f0f6fa] text-[#245275] border border-[#dce8f0]">
      Excel workbook
    </span>
  </div>
  <div className="text-xs font-mono text-zinc-400">epms.ppra.gov.pk</div>
</div>
```

### 3.4 3-Step "How It Works" Section
- 3-column layout separated by light border rule.
- Step numbering in gold serif (`01`, `02`, `03`).
- Clean serif titles:
  1. `Choose a source and scope`
  2. `The crawler does the reading`
  3. `Take away a spreadsheet`

### 3.5 Dark Callout Hero Banner
- Wide `rounded-3xl` container in `bg-[#0f1f38] text-white py-14 px-8 text-center`.
- Heading: `font-serif text-3xl font-normal`.
- Subtext: `text-sm text-zinc-300 max-w-xl mx-auto`.
- Light button CTA: `bg-white text-[#0f1f38] hover:bg-zinc-100 px-6 py-2.5 rounded-lg text-xs font-medium`.

### 3.6 Portal Console & Filter Matrix Form
- **Header Breadcrumbs & Navigation**:
  - Left: Logo + region badge `[us US] [PK]`.
  - Top Tabs: `Console` (active underline), `History`, `Downloads`.
  - Right: `1 source` pill badge, `API docs`.
- **Left Portal Sidebar**:
  - Clean light background (`bg-[#fbfaf8]`).
  - Active item: White card box with green left accent border, crescent icon, bold portal name, and subtext.
- **Console Filter Card**:
  - Title: `PPRA Search & Filter Criteria` with subtext `Filter active federal tenders published by the Public Procurement Regulatory Authority (epms.ppra.gov.pk).`
  - Grid: 3-column inputs:
    - Row 1: `Keyword Search`, `Tender Number`, `Closing Date` (with calendar picker).
    - Row 2: `Tender Type` (dropdown), `Category` (dropdown), `Sector` (dropdown).
    - Row 3: `Nature` (dropdown), `Organization / Ministry`, `Country` (default 'Pakistan').
    - Row 4: `Advertise Date From`, `Advertise Date To`, `Status` (dropdown).
    - Row 5: `City`.
  - Checkbox option: `[x] Apply 7-day runway closing filter (drop tenders closing in < 7 days)`.
  - Card Footer: Status text on left (`PPRA active tenders scraper ready with cooperative pause/resume and live tracking.`), buttons on right (`Refresh`, `▶ Start PPRA Scrape` in navy).

---

## 4. Typography Rules

Include Google Font **Newsreader** or **Playfair Display** (or serif system stack) for all headings:
```typescript
// layout.tsx
import { Inter, Newsreader } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const serif = Newsreader({ subsets: ["latin"], variable: "--font-serif", style: "normal" });
```
In `globals.css`:
```css
@import "tailwindcss";

@layer base {
  body {
    background-color: #faf8f5;
    color: #1e293b;
    font-family: var(--font-sans), system-ui, sans-serif;
  }
  h1, h2, h3, .font-editorial {
    font-family: var(--font-serif), Georgia, serif;
  }
}
```

---

## 5. UI Do's and Don'ts

| Do | Don't |
|----|-------|
| Use `#faf8f5` warm cream background for canvas | Don't use cold gray or stark stark white canvas |
| Use editorial serif headings for titles & cards | Don't use generic all-sans everywhere |
| Use high-contrast midnight navy (`#0f1f38`) for buttons & callouts | Don't use neon green or US-style blue buttons |
| Use emerald green sparingly for emblems & badges | Don't make the entire background green |
| Use rounded-2xl cards with fine hairline borders (`#e8e4dc`) | Don't use heavy drop-shadows |
