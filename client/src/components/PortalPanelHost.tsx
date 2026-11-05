"use client";

import PpraPanel from "@/components/PpraPanel";
import PunjabPanel from "@/components/PunjabPanel";
import type { Portal } from "@/lib/api";

/** Renders the portal panel from the console layout, so a running scrape keeps
 *  its view while the user visits History or Downloads. */
export default function PortalPanelHost({ visible, portal }: { visible: boolean; portal: Portal }) {
  if (!visible) return null;
  return (
    <div className="w-full">
      {portal === "punjab" ? <PunjabPanel /> : <PpraPanel />}
    </div>
  );
}
