"use client";

import PpraPanel from "@/components/PpraPanel";

/** Renders the portal panel from the console layout, so a running scrape keeps
 *  its view while the user visits History or Downloads. */
export default function PortalPanelHost({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="w-full">
      <PpraPanel />
    </div>
  );
}
