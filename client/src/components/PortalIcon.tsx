/** Line-art crescent and star: the PPRA / Pakistan portal glyph. */
export default function PortalIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M14.5 4.5A7.5 7.5 0 1 0 18 16a8.5 8.5 0 0 1-3.5-11.5Z" />
      <path
        d="M16 6.5l.6 1.3 1.4.2-1 1 .2 1.4-1.2-.7-1.2.7.2-1.4-1-1 1.4-.2z"
        fill="currentColor"
        stroke="none"
      />
    </svg>
  );
}
