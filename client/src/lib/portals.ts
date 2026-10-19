import type { Portal } from "@/lib/api";

export interface PortalMeta {
  key: Portal;
  label: string;
  tagline: string;
  description: string;
  accent: {
    tile: string;
    dot: string;
  };
}

export const PORTALS: PortalMeta[] = [
  {
    key: "ppra",
    label: "PPRA Pakistan",
    tagline: "Federal e-Procurement active tenders",
    description:
      "Automate public tender discovery across Pakistan's federal e-Procurement system (EPMS), filter by organization, sector, category and closing date, and export all matching active notices into structured Excel workbooks.",
    accent: {
      tile: "bg-emerald-50 text-emerald-800 ring-emerald-200",
      dot: "bg-emerald-500",
    },
  },
];

export function isPortal(val: unknown): val is Portal {
  return typeof val === "string" && PORTALS.some((p) => p.key === val);
}

export function portalMeta(portal: Portal): PortalMeta {
  return PORTALS.find((p) => p.key === portal) ?? PORTALS[0];
}

export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? `${count} ${singular}` : `${count} ${plural}`;
}
