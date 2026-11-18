import type { Portal } from "@/lib/api";

export interface PortalMeta {
  key: Portal;
  label: string;
  /** Two-letter prefix on every run serial from this portal. */
  code: string;
  tagline: string;
  description: string;
}

export const PORTALS: PortalMeta[] = [
  {
    key: "ppra",
    label: "PPRA Pakistan",
    code: "PK",
    tagline: "Federal EPMS",
    description:
      "Automate public tender discovery across Pakistan's federal e-Procurement system (EPMS), filter by organization, sector, category and closing date, and export all matching active notices into structured Excel workbooks.",
  },
  {
    key: "punjab",
    label: "PPRA Punjab",
    code: "PB",
    tagline: "e-Proc Active Tenders",
    description:
      "Collect live tenders from the Punjab e-Procurement portal, filter by type, title, department and closing date, leave out auctions, and export every match with its notice and bidding document links into structured Excel workbooks.",
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

/**
 * A run's serial, printed like a security document's: the portal's code and
 * the run id in groups of four. `PB · C5C9 F5F7 64BD`. The run id is the
 * server's own; nothing here is invented.
 */
export function runSerial(portal: Portal, runId: string): string {
  const groups = runId.toUpperCase().match(/.{1,4}/g) ?? [runId];
  return `${portalMeta(portal).code} · ${groups.join(" ")}`;
}

/** The short form for chips and narrow rows: `PB-C5C9`. */
export function runSerialShort(portal: Portal, runId: string): string {
  return `${portalMeta(portal).code}-${runId.slice(0, 4).toUpperCase()}`;
}
