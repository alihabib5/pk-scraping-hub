"use client";

import PpraPanel from "@/components/PpraPanel";

export default function PortalPanelHost({
  portal,
  visible = true,
}: {
  portal?: string | null;
  visible?: boolean;
}) {
  if (!visible) return null;
  return (
    <div className="w-full">
      <PpraPanel />
    </div>
  );
}
