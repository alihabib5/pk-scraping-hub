import type { PortalMeta } from "@/lib/portals";

/**
 * Line-art glyph for Pakistan procurement portals.
 */
export default function PortalIcon({
  name,
  className = "h-5 w-5",
}: {
  name: PortalMeta["icon"];
  className?: string;
}) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    "aria-hidden": true,
  };

  // Crescent and star: Pakistan / PPRA national procurement emblem.
  return (
    <svg {...common}>
      <path d="M14.5 4.5A7.5 7.5 0 1 0 18 16a8.5 8.5 0 0 1-3.5-11.5Z" />
      <path
        d="M16 6.5l.6 1.3 1.4.2-1 1 .2 1.4-1.2-.7-1.2.7.2-1.4-1-1 1.4-.2z"
        fill="currentColor"
        stroke="none"
      />
    </svg>
  );
}
