/**
 * The run's guilloché rosette: one ring per page of results, drawn as the
 * scraper reads it. The newest ring traces itself in; rings still to come are
 * faint. Red while the run is in flight, intaglio green once it is validated.
 */

/** Past this many pages the rings would merge into a solid disc. */
const MAX_RINGS = 24;
const RX = 62;
const RY = 24;
/** Ramanujan's approximation, good to well under a pixel here. */
const RING_LENGTH = Math.PI * (3 * (RX + RY) - Math.sqrt((3 * RX + RY) * (RX + 3 * RY)));

export default function Rosette({
  read,
  total,
  live,
  size = 140,
  drawIn = false,
}: {
  /** Pages read so far. */
  read: number;
  /** Pages the portal reported, or null while unknown. */
  total: number | null | undefined;
  /** In flight: drawn in serial red, newest ring animating. */
  live: boolean;
  size?: number;
  /** Trace every drawn ring in, one after another, once. */
  drawIn?: boolean;
}) {
  const known = total && total > 0 ? total : null;
  const rings = known ? Math.min(known, MAX_RINGS) : 12;
  // Map pages onto rings when a long run has more pages than rings.
  const drawn = known ? Math.round((Math.min(read, known) / known) * rings) : 0;
  const ink = live ? "var(--color-serial-600)" : "var(--color-intaglio-800)";

  return (
    <svg
      viewBox="-75 -75 150 150"
      width={size}
      height={size}
      role="img"
      aria-label={known ? `${read} of ${known} pages read` : "Page count not known yet"}
      className="shrink-0"
    >
      <circle r="71" fill="none" stroke="var(--color-ink-200)" strokeDasharray="2 3" />
      {Array.from({ length: rings }, (_, i) => {
        const done = i < drawn;
        const newest = live && i === drawn - 1;
        const traced = newest || (drawIn && done);
        return (
          <ellipse
            key={`${i}-${newest ? read : "x"}`}
            rx={RX}
            ry={RY}
            transform={`rotate(${(180 / rings) * i})`}
            fill="none"
            stroke={done ? ink : "var(--color-ink-200)"}
            strokeWidth={done ? 0.9 : 0.5}
            strokeOpacity={done ? 0.9 : 0.7}
            className={traced ? "ring-trace" : undefined}
            style={
              traced
                ? ({
                    "--ring-length": RING_LENGTH,
                    animationDelay: drawIn ? `${i * 120}ms` : undefined,
                  } as React.CSSProperties)
                : undefined
            }
          />
        );
      })}
      <circle r="21" fill="var(--color-sheet)" stroke="var(--color-ink-200)" strokeWidth="0.8" />
      <text
        y="5"
        textAnchor="middle"
        className="font-mono"
        fontSize="14"
        fontWeight="700"
        fill="var(--color-ink-900)"
      >
        {known ? `${Math.min(read, known)}/${known}` : "—"}
      </text>
    </svg>
  );
}
