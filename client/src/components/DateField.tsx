"use client";

import { useEffect, useRef, useState } from "react";

import { Button, CONTROL } from "@/components/ui";

/**
 * Date picker for the filter forms. Replaces the browser's `<input type="date">`,
 * whose popup and "dd/mm/yyyy" placeholder differ in every browser and clash
 * with the rest of the form.
 *
 * Shape: the rounded-selected-day calendar (shadcn "calendar-13"), recoloured
 * for PK-Hub. Navy marks the chosen day because navy is this app's committing
 * colour; gold ring marks today because gold is accent only. Day circles are
 * 36px and the card is 288px so it sits comfortably under a `text-sm` control.
 *
 * The value stays a plain "YYYY-MM-DD" string ("" = no date), exactly what the
 * old input produced, so callers and the API are unchanged.
 */

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const POPOVER_WIDTH = 288; // matches w-72

const pad = (n: number) => String(n).padStart(2, "0");
/** `m` is 0-based, like Date. */
const isoOf = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`;
const isoFromDate = (d: Date) => isoOf(d.getFullYear(), d.getMonth(), d.getDate());

/** Local day, not UTC: `toISOString()` shows yesterday for the first hours of a Pakistan morning. */
const todayIso = () => isoFromDate(new Date());

function parseIso(iso: string): [number, number, number] | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const [y, mo, d] = [Number(m[1]), Number(m[2]) - 1, Number(m[3])];
  const check = new Date(y, mo, d);
  return check.getFullYear() === y && check.getMonth() === mo && check.getDate() === d ? [y, mo, d] : null;
}

/** "2 Nov 2026", or "" for an empty or unreadable value. */
export function formatDate(iso: string): string {
  const p = parseIso(iso);
  return p ? `${p[2]} ${MONTHS[p[1]].slice(0, 3)} ${p[0]}` : "";
}

const NAV_BUTTON =
  "flex h-8 w-8 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 hover:text-ink-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-500";

function dayClass(selected: boolean, today: boolean, outside: boolean): string {
  const base =
    "mx-auto flex h-9 w-9 items-center justify-center rounded-full text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-gold-500";
  if (selected) return `${base} bg-ink-900 font-semibold text-white hover:bg-ink-800`;
  if (today) return `${base} font-semibold text-ink-900 ring-2 ring-inset ring-gold-500 hover:bg-gold-50`;
  return `${base} font-medium ${outside ? "text-ink-500" : "text-ink-900"} hover:bg-ink-100`;
}

export default function DateField({
  label,
  value,
  onChange,
  disabled,
  placeholder = "Select date",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"days" | "months">("days");
  const [year, setYear] = useState(0);
  const [month, setMonth] = useState(0);
  const [focusIso, setFocusIso] = useState("");
  const [alignRight, setAlignRight] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const popover = useRef<HTMLDivElement>(null);
  // Focus moves only when the user navigated by keyboard or opened the picker;
  // clicking the month arrows must leave focus on the arrow.
  const refocus = useRef(false);
  const triggerId = `date-${label.replace(/\s+/g, "-").toLowerCase()}`;

  useEffect(() => {
    if (!open || !refocus.current) return;
    refocus.current = false;
    popover.current?.querySelector<HTMLElement>('[data-focus="true"]')?.focus();
  });

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const openPicker = () => {
    const p = parseIso(value) ?? parseIso(todayIso());
    if (!p) return;
    setYear(p[0]);
    setMonth(p[1]);
    setFocusIso(isoOf(p[0], p[1], p[2]));
    setView("days");
    const rect = wrap.current?.getBoundingClientRect();
    setAlignRight(!!rect && rect.left + POPOVER_WIDTH > window.innerWidth - 8);
    refocus.current = true;
    setOpen(true);
  };

  const close = (returnFocus: boolean) => {
    setOpen(false);
    if (returnFocus) trigger.current?.focus();
  };

  const pick = (iso: string) => {
    onChange(iso);
    close(true);
  };

  const goToMonth = (y: number, m: number) => {
    const t = new Date(y, m, 1);
    setYear(t.getFullYear());
    setMonth(t.getMonth());
    setFocusIso(isoFromDate(t));
  };

  const moveFocus = (days: number) => {
    const p = parseIso(focusIso);
    if (!p) return;
    const n = new Date(p[0], p[1], p[2] + days);
    setFocusIso(isoFromDate(n));
    setYear(n.getFullYear());
    setMonth(n.getMonth());
    refocus.current = true;
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      close(true);
      return;
    }
    const target = e.target as HTMLElement;
    if (view !== "days" || !target.dataset.d) return;
    const steps: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    if (e.key in steps) {
      e.preventDefault();
      moveFocus(steps[e.key]);
    } else if (e.key === "PageUp" || e.key === "PageDown") {
      e.preventDefault();
      const p = parseIso(focusIso);
      if (!p) return;
      const delta = e.key === "PageUp" ? -1 : 1;
      const lastDay = new Date(p[0], p[1] + delta + 1, 0).getDate();
      const n = new Date(p[0], p[1] + delta, Math.min(p[2], lastDay));
      setFocusIso(isoFromDate(n));
      setYear(n.getFullYear());
      setMonth(n.getMonth());
      refocus.current = true;
    }
  };

  const today = todayIso();
  const firstOffset = (new Date(year, month, 1).getDay() + 6) % 7; // Monday first

  return (
    <div>
      <label htmlFor={triggerId} className="mb-1.5 block text-xs font-semibold text-ink-700">
        {label}
      </label>
      <div
        ref={wrap}
        className="relative"
        onBlur={(e) => {
          const next = e.relatedTarget as Node | null;
          if (open && next && !e.currentTarget.contains(next)) setOpen(false);
        }}
      >
        <button
          type="button"
          id={triggerId}
          ref={trigger}
          disabled={disabled}
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => (open ? close(true) : openPicker())}
          className={`${CONTROL} flex items-center justify-between gap-2 text-left`}
        >
          <span className={value ? "" : "text-ink-400"}>{formatDate(value) || placeholder}</span>
          <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-ink-500" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
            <path d="M5 5h14v15H5zM5 10h14M9 3v4M15 3v4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {open && (
          <div
            ref={popover}
            role="dialog"
            aria-label={`Choose ${label.toLowerCase()}`}
            onKeyDown={onKeyDown}
            className={`absolute z-30 mt-1 w-72 rounded-[1.75rem] border border-ink-200 bg-white p-3 shadow-lg shadow-ink-900/[0.08] ${
              alignRight ? "right-0" : "left-0"
            }`}
          >
            {view === "months" ? (
              <>
                <div className="mb-1 flex items-center justify-between">
                  <button type="button" className={NAV_BUTTON} aria-label="Previous year" onClick={() => setYear(year - 1)}>
                    <Chevron dir={-1} />
                  </button>
                  <span className="font-display text-base text-ink-900" aria-live="polite">
                    {year}
                  </span>
                  <button type="button" className={NAV_BUTTON} aria-label="Next year" onClick={() => setYear(year + 1)}>
                    <Chevron dir={1} />
                  </button>
                </div>
                <div role="group" aria-label="Months" className="grid grid-cols-3 gap-1.5 py-1">
                  {MONTHS.map((name, i) => {
                    const current = parseIso(value);
                    const selected = !!current && current[0] === year && current[1] === i;
                    const thisMonth = isoFromDate(new Date()).slice(0, 7) === `${year}-${pad(i + 1)}`;
                    return (
                      <button
                        key={name}
                        type="button"
                        data-focus={i === month}
                        data-m={i}
                        aria-pressed={selected}
                        onClick={() => {
                          goToMonth(year, i);
                          setView("days");
                          refocus.current = true;
                        }}
                        className={`h-10 rounded-full text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-500 ${
                          selected
                            ? "bg-ink-900 font-semibold text-white hover:bg-ink-800"
                            : thisMonth
                              ? "font-semibold text-ink-900 ring-2 ring-inset ring-gold-500 hover:bg-gold-50"
                              : "font-medium text-ink-900 hover:bg-ink-100"
                        }`}
                      >
                        {name.slice(0, 3)}
                      </button>
                    );
                  })}
                </div>
              </>
            ) : (
              <>
                <div className="mb-1 flex items-center justify-between">
                  <button type="button" className={NAV_BUTTON} aria-label="Previous month" onClick={() => goToMonth(year, month - 1)}>
                    <Chevron dir={-1} />
                  </button>
                  <button
                    type="button"
                    data-cap
                    onClick={() => {
                      setView("months");
                      refocus.current = true;
                    }}
                    aria-label={`${MONTHS[month]} ${year}, choose month`}
                    className="rounded-full px-3 py-1 font-display text-base text-ink-900 transition hover:bg-ink-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-500"
                  >
                    {MONTHS[month]} {year}
                  </button>
                  <button type="button" className={NAV_BUTTON} aria-label="Next month" onClick={() => goToMonth(year, month + 1)}>
                    <Chevron dir={1} />
                  </button>
                </div>
                <div className="grid grid-cols-7 text-center" aria-hidden>
                  {WEEKDAYS.map((d) => (
                    <span key={d} className="py-1.5 text-xs font-semibold text-ink-500">
                      {d}
                    </span>
                  ))}
                </div>
                <div role="group" aria-label={`${MONTHS[month]} ${year}`} className="grid grid-cols-7 gap-y-0.5">
                  {Array.from({ length: 42 }, (_, i) => {
                    const d = new Date(year, month, 1 - firstOffset + i);
                    const iso = isoFromDate(d);
                    const selected = iso === value;
                    return (
                      <button
                        key={iso}
                        type="button"
                        data-d={iso}
                        data-focus={iso === focusIso}
                        tabIndex={iso === focusIso ? 0 : -1}
                        aria-label={`${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`}
                        aria-pressed={selected}
                        aria-current={iso === today ? "date" : undefined}
                        onClick={() => pick(iso)}
                        className={dayClass(selected, iso === today, d.getMonth() !== month)}
                      >
                        {d.getDate()}
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            <div className="mt-2 flex items-center justify-between border-t border-ink-100 pt-2">
              <div className="flex items-center gap-1">
                <Button type="button" variant="ghost" size="sm" onClick={() => pick(today)}>
                  Today
                </Button>
                {value && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => pick("")}>
                    Clear
                  </Button>
                )}
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={() => close(true)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Chevron({ dir }: { dir: -1 | 1 }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d={dir < 0 ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
