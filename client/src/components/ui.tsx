"use client";

import { useEffect, useRef, useState, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type ReactNode } from "react";

import type { RunStatus } from "@/lib/api";

/**
 * The button scale. `primary` (navy) is reserved for the one committing action
 * on a view; everything else is `secondary` or `ghost`, so a page never has two
 * things competing to be pressed. Gold appears only as accent, never as a fill.
 */
type Variant = "primary" | "secondary" | "ghost" | "danger" | "warning" | "success";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-ink-900 text-white ring-1 ring-ink-900 shadow-sm hover:bg-ink-800 hover:ring-ink-800 disabled:bg-ink-100 disabled:text-ink-400 disabled:ring-ink-100 disabled:shadow-none",
  secondary:
    "bg-white text-ink-800 ring-1 ring-ink-200 shadow-sm hover:bg-ink-50 hover:ring-ink-300 disabled:text-ink-300 disabled:shadow-none",
  ghost: "text-ink-600 hover:bg-ink-50 hover:text-ink-900 disabled:text-ink-300",
  danger: "bg-white text-red-700 ring-1 ring-red-200 shadow-sm hover:bg-red-50 disabled:text-red-300",
  // Hold, not stop. Amber and outlined so it reads as a reversible interruption
  // sitting next to Stop's red without competing with it.
  warning:
    "bg-amber-50 text-amber-800 ring-1 ring-amber-300 shadow-sm hover:bg-amber-100 hover:ring-amber-400 disabled:bg-amber-50/60 disabled:text-amber-300 disabled:ring-amber-100",
  // Release. Filled green, because a parked run has exactly one obvious next
  // move and it should look like the thing to press.
  success:
    "bg-emerald-600 text-white ring-1 ring-emerald-600 shadow-sm hover:bg-emerald-700 hover:ring-emerald-700 disabled:bg-emerald-200 disabled:ring-emerald-200 disabled:shadow-none",
};

const SIZES = {
  sm: "px-2.5 py-1.5 text-xs gap-1.5",
  md: "px-4 py-2.5 text-sm gap-2",
  lg: "px-5 py-3 text-sm gap-2",
};

const BUTTON_BASE =
  "inline-flex items-center justify-center rounded-lg font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold-500 disabled:cursor-not-allowed";

export function Button({
  variant = "secondary",
  size = "md",
  loading,
  icon,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: keyof typeof SIZES;
  loading?: boolean;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      {...props}
      disabled={props.disabled || loading}
      className={`${BUTTON_BASE} ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  );
}

/** Anchor styled as a button — for real navigation and downloads. */
export function LinkButton({
  variant = "secondary",
  size = "md",
  icon,
  children,
  className = "",
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: Variant;
  size?: keyof typeof SIZES;
  icon?: ReactNode;
}) {
  return (
    <a {...props} className={`${BUTTON_BASE} ${SIZES[size]} ${VARIANTS[variant]} ${className}`}>
      {icon}
      {children}
    </a>
  );
}

/** Square button for a bare icon. `label` is required — it's the only a11y name. */
export function IconButton({
  label,
  variant = "ghost",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; variant?: Variant }) {
  return (
    <button
      type="button"
      {...props}
      aria-label={label}
      title={label}
      className={`${BUTTON_BASE} h-9 w-9 shrink-0 ${VARIANTS[variant]}`}
    >
      {children}
    </button>
  );
}

export function Spinner({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return <span className={`${className} animate-spin rounded-full border-2 border-current/30 border-t-current`} />;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-ink-200 bg-white/70 px-6 py-16 text-center">
      {icon && (
        <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-gold-50 text-gold-600 ring-1 ring-gold-100">
          {icon}
        </span>
      )}
      <h3 className="font-display text-lg text-ink-900">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-ink-500">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/** Primary call-to-action used to launch a scrape. */
export function StartButton({
  running,
  starting,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { running?: boolean; starting?: boolean }) {
  const label = running ? "Run in progress…" : starting ? "Starting…" : children;
  return (
    <Button {...props} variant="primary" size="lg" loading={running || starting} icon={<PlayIcon />}>
      {label}
    </Button>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <svg viewBox="0 0 20 20" fill="currentColor" className="mt-0.5 h-4 w-4 shrink-0 text-red-500" aria-hidden>
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm.75-11.25a.75.75 0 0 0-1.5 0v3.5a.75.75 0 0 0 1.5 0v-3.5Zm-.75 7.5a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8Z"
          clipRule="evenodd"
        />
      </svg>
      <span>{message}</span>
    </div>
  );
}

/** White panel grouping one logical step of the configuration form. */
export function Card({
  title,
  description,
  actions,
  children,
}: {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-ink-200/70 bg-white shadow-sm shadow-ink-900/[0.03]">
      {(title || actions) && (
        <header className="flex items-start justify-between gap-4 border-b border-ink-100 px-5 py-4">
          <div>
            {title && <h3 className="font-display text-base text-ink-900">{title}</h3>}
            {description && <p className="mt-0.5 text-xs leading-relaxed text-ink-500">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-1">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

/** The shared look of every form control. */
const CONTROL =
  "w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 shadow-sm transition placeholder:text-ink-400 focus:border-gold-400 focus:outline-none focus:ring-2 focus:ring-gold-400/25 disabled:cursor-not-allowed disabled:bg-ink-50 disabled:text-ink-400";

/** Text input with a label, matching the form language of the rest of the app. */
export function Field({
  label,
  hint,
  value,
  onChange,
  disabled,
  placeholder,
  type = "text",
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold text-ink-700">{label}</label>
      <input
        type={type}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={CONTROL}
      />
      {hint && <p className="mt-1.5 text-xs text-ink-500">{hint}</p>}
    </div>
  );
}

/** A labelled dropdown for a short list. The empty value means "any". */
export function SelectField({
  label,
  value,
  options,
  onChange,
  disabled,
  placeholder,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold text-ink-700">{label}</label>
      <select value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} className={CONTROL}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/** How many matches the search picker renders at once; typing narrows the rest. */
const SEARCH_LIMIT = 80;

/**
 * A labelled, type-to-search picker for a long list (1,200+ organizations).
 * Shows the chosen label; clicking, focusing or typing opens the list to filter.
 * The empty value means "any". Arrow keys move, Enter picks, Escape closes.
 */
export function SearchSelect({
  label,
  value,
  options,
  onChange,
  disabled,
  placeholder,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = options.find((o) => o.value === value);
  const q = query.trim().toLowerCase();
  const matches = q ? options.filter((o) => o.label.toLowerCase().includes(q)) : options;
  // The "any" choice first, so a selection can always be cleared.
  const shown = [{ value: "", label: placeholder }, ...matches.slice(0, SEARCH_LIMIT)];

  const openList = (initialQuery = "") => {
    setOpen(true);
    setQuery(initialQuery);
    setActive(0);
  };

  const pick = (next: string) => {
    onChange(next);
    setOpen(false);
    setQuery("");
  };

  useEffect(() => {
    listRef.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [active]);

  return (
    <div className="relative">
      <label className="mb-1.5 block text-xs font-semibold text-ink-700">{label}</label>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          disabled={disabled}
          value={open ? query : (selected?.label ?? "")}
          placeholder={open ? `Search ${options.length.toLocaleString()} options…` : placeholder}
          onFocus={() => openList()}
          // After a pick the box keeps focus, so focus alone can't reopen it.
          onClick={() => {
            if (!open) openList();
          }}
          onBlur={() => setOpen(false)}
          onChange={(e) => {
            if (open) {
              setQuery(e.target.value);
              setActive(0);
            } else {
              // Typing into a closed box: the box showed the chosen label, so
              // keep only what was typed after it.
              const shownLabel = selected?.label ?? "";
              const typed = e.target.value;
              openList(typed.startsWith(shownLabel) ? typed.slice(shownLabel.length) : typed);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              if (!open) openList();
              else setActive((i) => Math.min(i + 1, shown.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((i) => Math.max(i - 1, 0));
            } else if (e.key === "Enter" && open) {
              e.preventDefault();
              pick(shown[active].value);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          className={`${CONTROL} pr-9`}
        />
        <button
          type="button"
          tabIndex={-1}
          aria-label={open ? `Close ${label} list` : `Open ${label} list`}
          disabled={disabled}
          // mousedown + preventDefault keeps focus in the box, so closing doesn't blur it.
          onMouseDown={(e) => {
            e.preventDefault();
            if (open) {
              setOpen(false);
            } else {
              inputRef.current?.focus();
              openList();
            }
          }}
          className="absolute inset-y-0 right-0 flex w-9 items-center justify-center text-ink-400 transition hover:text-ink-700 disabled:cursor-not-allowed disabled:text-ink-300"
        >
          <svg
            viewBox="0 0 16 16"
            className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            aria-hidden
          >
            <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
      {open && (
        <ul
          ref={listRef}
          role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-ink-200 bg-white py-1 text-sm shadow-lg"
        >
          {shown.map((option, i) => (
            <li
              key={option.value || "__any"}
              role="option"
              aria-selected={option.value === value}
              // mousedown, not click: it fires before the input's blur closes the list.
              onMouseDown={(e) => {
                e.preventDefault();
                pick(option.value);
              }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer px-3 py-1.5 ${i === active ? "bg-gold-50 text-ink-900" : "text-ink-700"} ${
                option.value === "" ? "text-ink-500" : ""
              }`}
            >
              {option.label}
            </li>
          ))}
          {matches.length > SEARCH_LIMIT && (
            <li className="px-3 py-1.5 text-xs text-ink-400">
              {(matches.length - SEARCH_LIMIT).toLocaleString()} more — keep typing to narrow
            </li>
          )}
          {q && matches.length === 0 && <li className="px-3 py-1.5 text-xs text-ink-400">No match</li>}
        </ul>
      )}
    </div>
  );
}

/** Shared table shell: bordered, scrollable, with a quiet header row. */
export function DataTable({
  headers,
  caption,
  children,
}: {
  headers: { label: string; className?: string }[];
  caption?: string;
  children: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-ink-200/70 bg-white shadow-sm shadow-ink-900/[0.03]">
      {caption && (
        <div className="border-b border-ink-100 px-5 py-4">
          <h3 className="font-display text-base text-ink-900">{caption}</h3>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink-200 bg-ink-50/70 text-left text-xs font-semibold text-ink-600">
              {headers.map((h) => (
                <th key={h.label} className={`whitespace-nowrap px-4 py-3 ${h.className ?? ""}`}>
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">{children}</tbody>
        </table>
      </div>
    </div>
  );
}

/** Run lifecycle badge — shared by the live monitor and the history table.
 *
 *  The status type is taken from `RunStatus` rather than written out again: the
 *  two copies had already drifted once (a new state was added to the API's union
 *  and this one silently rejected it), and one of them being a duplicate is what
 *  made that possible. */
export function RunBadge({
  status,
  partial,
}: {
  status: RunStatus["status"];
  /** A stopped run that kept what it had gathered. Shown on the badge because
   *  "Stopped" alone used to mean "and nothing came of it", and a reviewer who
   *  reads it that way never looks for the download that is now sitting there. */
  partial?: boolean;
}) {
  const map = {
    // pending is the instant between the run being registered and the pool
    // accepting it; queued is waiting for a slot. Both read as "Queued" to a
    // user — the distinction only matters inside the server.
    pending: { cls: "border-ink-200 bg-ink-50 text-ink-600", label: "Queued" },
    queued: { cls: "border-ink-200 bg-ink-50 text-ink-600", label: "Queued" },
    running: { cls: "border-gold-300 bg-gold-50 text-gold-700", label: "Running" },
    completed: { cls: "border-emerald-200 bg-emerald-50 text-emerald-700", label: "Completed" },
    failed: { cls: "border-red-200 bg-red-50 text-red-700", label: "Failed" },
    stopped: { cls: "border-ink-300 bg-ink-100 text-ink-700", label: "Stopped" },
    // Amber, and deliberately not pulsing: a parked run is holding, not
    // working, and a badge that throbbed would say the opposite.
    paused: { cls: "border-amber-300 bg-amber-50 text-amber-700", label: "Paused" },
  }[status];
  const live = status === "running" || status === "pending" || status === "queued";
  // Amber rather than the neutral stopped grey: there is something to collect,
  // and grey is the colour this console uses for "nothing happened here".
  const showPartial = partial && status === "stopped";
  const cls = showPartial
    ? "border-amber-300 bg-amber-50 text-amber-800"
    : map.cls;
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {live && <span className="status-pulse h-1.5 w-1.5 rounded-full bg-current" />}
      {showPartial ? "Stopped — partial results" : map.label}
    </span>
  );
}

/**
 * Sticky action bar holding the run trigger. Anchoring it to the bottom of the
 * viewport keeps the button reachable on long configuration forms.
 */
export function LaunchBar({ summary, children }: { summary: ReactNode; children: ReactNode }) {
  return (
    <div className="sticky bottom-4 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink-200/70 bg-white/95 px-5 py-4 shadow-lg shadow-ink-900/[0.06] backdrop-blur">
      <div className="min-w-0 text-sm text-ink-500">{summary}</div>
      {children}
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor" aria-hidden>
      <path d="M4 3.5v9a.5.5 0 0 0 .77.42l7-4.5a.5.5 0 0 0 0-.84l-7-4.5A.5.5 0 0 0 4 3.5Z" />
    </svg>
  );
}

