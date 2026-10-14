"use client";

import PpraResults from "@/components/PpraResults";
import type { Portal } from "@/lib/api";

export type BidResult = Record<string, any>;

/**
 * Renders the results table for the active portal.
 */
export default function PortalResults({
  portal,
  bids,
}: {
  portal: Portal;
  bids: BidResult[];
}) {
  return <PpraResults initialBids={bids} />;
}
