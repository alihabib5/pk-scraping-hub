/** The seal: a small guilloché rosette in ochre, as on a stamp paper's corner. */
export default function Logo({ className = "h-8 w-8" }: { className?: string }) {
  const petals = Array.from({ length: 8 }, (_, i) => i * 22.5);
  return (
    <svg viewBox="-20 -20 40 40" className={`${className} shrink-0`} aria-hidden>
      <circle r="19" fill="var(--color-intaglio-950)" stroke="var(--color-ochre-400)" strokeWidth="1.2" />
      <g fill="none" stroke="var(--color-ochre-400)" strokeWidth="0.7">
        {petals.map((deg) => (
          <ellipse key={deg} rx="14" ry="5.5" transform={`rotate(${deg})`} />
        ))}
      </g>
      <circle r="2.4" fill="var(--color-ochre-300)" />
    </svg>
  );
}
