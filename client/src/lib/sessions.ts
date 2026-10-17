"use client";

import { useCallback, useSyncExternalStore } from "react";

import {
  isRunActive,
  isTerminalStatus,
  type Job,
  type JobCapacity,
  type JobLogLine,
  type Portal,
  type RunStatus,
} from "@/lib/api";

/**
 * The console's scrape sessions, held outside React.
 *
 * A run belongs to the server, not to the page that started it. One slot per
 * portal lives at module scope, fed by a single engine (see SessionEngine) that
 * runs for as long as the console is open. Panels read their slot and render
 * it; nothing they do — mounting, unmounting, navigating — starts or stops any
 * polling, so moving between the console's tabs never loses a running scrape.
 */

export interface Session {
  portal: Portal;
  runId: string;
  /** Latest full status from the run's own endpoint — the panel's whole view. */
  run: RunStatus | null;
  /** Streaming log tail, newest last, capped so a long run cannot grow forever. */
  logs: JobLogLine[];
  /** Highest log sequence number seen, so each poll asks only for what is new. */
  logSeq: number;
  /** A launch or control failure worth showing in the panel's error banner. */
  error: string | null;
  /** True between pressing Start and the server handing back a run id. */
  starting: boolean;
  /** Wall-clock ms when this slot was last touched. */
  updatedAt: number;
  /**
   * Wall-clock ms when this run first reached a terminal status, or null while
   * it is still in flight (or has never run). This is what the TTL sweep reads.
   */
  completedAt: number | null;
}

/** How much log tail a slot keeps. Enough to scroll back through a stage. */
const LOG_LIMIT = 500;

/** Where the slot→run mapping survives a page reload. */
const STORAGE_KEY = "scraping-hub.sessions.v1";

/** An empty slot: a portal the user has opened but never launched. */
function blank(portal: Portal): Session {
  return {
    portal,
    runId: "",
    run: null,
    logs: [],
    logSeq: 0,
    error: null,
    starting: false,
    updatedAt: Date.now(),
    completedAt: null,
  };
}

// -- the store ---------------------------------------------------------------

type Slots = Readonly<Partial<Record<Portal, Session>>>;

let slots: Slots = {};
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

/** Replace one slot and notify. */
function write(portal: Portal, next: Session | null) {
  const copy: Partial<Record<Portal, Session>> = { ...slots };
  if (next) copy[portal] = { ...next, updatedAt: Date.now() };
  else delete copy[portal];
  slots = copy;
  persist();
  emit();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSlots(): Slots {
  return slots;
}

export function getSession(portal: Portal): Session | undefined {
  return slots[portal];
}

// -- reload persistence ------------------------------------------------------

/**
 * Only the identity of each slot's run is persisted — never the run's contents.
 * The server is the source of truth for status, counts and logs; what the
 * browser has to remember is which run this console considers to be occupying
 * which slot.
 */
interface Persisted {
  portal: Portal;
  runId: string;
}

function persist() {
  if (typeof window === "undefined") return;
  const rows: Persisted[] = Object.values(slots)
    .filter((s): s is Session => !!s && !!s.runId)
    .map((s) => ({ portal: s.portal, runId: s.runId }));
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
  } catch {
    // Private mode, or a full quota. Only the reload handoff is lost, and the
    // jobs poll re-adopts any run that is still going anyway.
  }
}

/** Re-seed the registry from the last page view. Called once by the engine. */
export function restore() {
  if (typeof window === "undefined") return;
  let rows: Persisted[] = [];
  try {
    rows = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return;
  }
  if (!Array.isArray(rows)) return;
  const copy: Partial<Record<Portal, Session>> = { ...slots };
  for (const row of rows) {
    if (!row?.portal || !row?.runId || copy[row.portal]) continue;
    copy[row.portal] = { ...blank(row.portal), runId: row.runId };
  }
  slots = copy;
  emit();
}

// -- actions -----------------------------------------------------------------

/** Start button pressed: clear the last error and show the launching state. */
export function beginLaunch(portal: Portal) {
  write(portal, { ...(slots[portal] ?? blank(portal)), starting: true, error: null });
}

/** The server accepted a run and named it. The previous run's status and logs
 *  are dropped: this is a new run in the slot. */
export function attachRun(portal: Portal, runId: string) {
  write(portal, { ...blank(portal), runId, starting: false });
}

/** A launch that never got a run id. */
export function failLaunch(portal: Portal, message: string) {
  write(portal, { ...(slots[portal] ?? blank(portal)), starting: false, error: message });
}

export function setSessionError(portal: Portal, message: string | null) {
  write(portal, { ...(slots[portal] ?? blank(portal)), error: message });
}

/** Fresh status from the engine's poll. `completedAt` is stamped the first tick
 *  a run is seen terminal and kept after, so re-polling doesn't push its expiry back. */
export function putRun(portal: Portal, run: RunStatus) {
  const current = slots[portal] ?? blank(portal);
  const completedAt = isTerminalStatus(run.status) ? (current.completedAt ?? Date.now()) : null;
  write(portal, { ...current, runId: run.run_id, run, starting: false, completedAt });
}

/** Apply a status the console itself just caused (pause, resume) without
 *  waiting for the next poll. */
export function patchRunStatus(portal: Portal, status: RunStatus["status"]) {
  const current = slots[portal];
  if (!current?.run) return;
  write(portal, { ...current, run: { ...current.run, status } });
}

/** New log lines from the tail poll. */
export function appendLogs(portal: Portal, lines: JobLogLine[], seq: number) {
  const current = slots[portal];
  if (!current || lines.length === 0) return;
  write(portal, {
    ...current,
    logs: [...current.logs, ...lines].slice(-LOG_LIMIT),
    logSeq: Math.max(seq, current.logSeq),
  });
}

/**
 * Adopt a run the console did not launch in this page view — one still going
 * after a reload, or started from another browser tab. Only ever fills an
 * empty slot: the panel's own launch is the authority on what it is watching.
 */
export function adopt(portal: Portal, runId: string) {
  const current = slots[portal];
  if (current?.runId) return;
  write(portal, { ...blank(portal), runId });
}

/**
 * Reset one portal's slot to its fresh, never-launched state — the panel's
 * Refresh button, and what the TTL sweep below calls once a finished slot has
 * gone stale. This never touches the server: a run still in flight keeps
 * running, and the next discovery tick re-adopts it, so callers that mean to
 * abort an active run stop it themselves first.
 */
export function resetScraperState(portal: Portal) {
  write(portal, null);
}

/** How long a finished slot stays on screen before it is swept. The rows are
 *  never at risk: they stay on the server and on the Downloads page. */
const SESSION_TTL_MS = 2 * 60 * 60 * 1000;

/** Reset every completed slot that has sat untouched past `SESSION_TTL_MS`.
 *  Called on every engine tick and on tab focus (browsers throttle timers in
 *  background tabs). */
export function expireStaleSessions(now: number = Date.now()) {
  for (const session of Object.values(slots)) {
    if (!session) continue;
    if (session.completedAt == null) continue;
    if (isRunActive(session.run)) continue; // resumed after being marked done — leave it
    if (now - session.completedAt >= SESSION_TTL_MS) resetScraperState(session.portal);
  }
}

// -- React bindings ----------------------------------------------------------

/**
 * One portal's slot, re-rendering only when that slot changes.
 * `getServerSnapshot` returns undefined: the registry is browser state, and
 * the prerendered HTML holds no session.
 */
export function useSession(portal: Portal): Session | undefined {
  return useSyncExternalStore(
    subscribe,
    useCallback(() => slots[portal], [portal]),
    () => undefined,
  );
}

/** Every slot, for anything that looks runs up by id. */
export function useSlots(): Slots {
  return useSyncExternalStore(subscribe, getSlots, () => EMPTY_SLOTS);
}

const EMPTY_SLOTS: Slots = {};

/**
 * The portals holding a live run right now. Read through a key string so
 * `useSyncExternalStore` can compare by value — a fresh array each call would
 * loop forever.
 */
export function useActivePortals(): Set<Portal> {
  const key = useSyncExternalStore(subscribe, activePortalKey, () => "");
  return new Set(key ? (key.split(",") as Portal[]) : []);
}

function activePortalKey(): string {
  return Object.values(slots)
    .filter((s): s is Session => !!s?.run && isRunActive(s.run))
    .map((s) => s.portal)
    .sort()
    .join(",");
}

/** Every slot holding a run, live or finished — the engine's work list. */
export function sessionsWithRuns(): Session[] {
  return Object.values(slots).filter((s): s is Session => !!s && !!s.runId);
}

// -- the jobs feed -----------------------------------------------------------

/**
 * `GET /runs?active=true` — every run in flight plus the pool's capacity. One
 * poll answers for the whole console, so the engine owns it and publishes the
 * result here rather than each consumer opening its own.
 */
interface JobsFeed {
  jobs: Job[];
  capacity: JobCapacity | null;
}

let feed: JobsFeed = { jobs: [], capacity: null };
const feedListeners = new Set<() => void>();

function subscribeFeed(listener: () => void) {
  feedListeners.add(listener);
  return () => {
    feedListeners.delete(listener);
  };
}

export function putJobsFeed(jobs: Job[], capacity: JobCapacity | null) {
  feed = { jobs, capacity };
  for (const l of feedListeners) l();
}

function getFeed(): JobsFeed {
  return feed;
}

const EMPTY_FEED: JobsFeed = { jobs: [], capacity: null };

export function useJobsFeed(): JobsFeed {
  return useSyncExternalStore(subscribeFeed, getFeed, () => EMPTY_FEED);
}
