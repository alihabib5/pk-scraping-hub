"use client";

import { useEffect, useState } from "react";

import { getPpraFilters, getPunjabFilters, listRuns, type Portal, type RunStatus } from "@/lib/api";

/** What the landing page can truthfully say, read live from the server. */
export interface LandingFacts {
  /** The newest completed run on any portal. */
  latest: RunStatus | null;
  runCounts: Record<Portal, number> | null;
  /** How many options the big filter on each portal offers. */
  listSizes: Partial<Record<Portal, { count: number; noun: string }>>;
}

const EMPTY: LandingFacts = { latest: null, runCounts: null, listSizes: {} };

/**
 * Live figures for the landing page. Every number on that page comes from
 * here; when the API is unreachable the page shows none rather than a guess.
 */
export function useLandingFacts(): LandingFacts {
  const [facts, setFacts] = useState<LandingFacts>(EMPTY);

  useEffect(() => {
    let cancelled = false;
    loadFacts().then((next) => {
      if (!cancelled) setFacts(next);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return facts;
}

/** One fetch per page load, shared by every part of the page that asks. */
let pending: Promise<LandingFacts> | null = null;

function loadFacts(): Promise<LandingFacts> {
  pending ??= Promise.allSettled([listRuns("ppra"), listRuns("punjab"), getPpraFilters(), getPunjabFilters()]).then(
      ([ppraRuns, punjabRuns, ppraLists, punjabLists]) => {
        const runs = [
          ...(ppraRuns.status === "fulfilled" ? ppraRuns.value.runs : []),
          ...(punjabRuns.status === "fulfilled" ? punjabRuns.value.runs : []),
        ];
        const latest =
          runs
            .filter((r) => r.status === "completed")
            .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0] ?? null;
        const listSizes: LandingFacts["listSizes"] = {};
        if (ppraLists.status === "fulfilled") {
          listSizes.ppra = { count: ppraLists.value.options.organization?.length ?? 0, noun: "organisations" };
        }
        if (punjabLists.status === "fulfilled") {
          listSizes.punjab = { count: punjabLists.value.options.department?.length ?? 0, noun: "departments" };
        }
        const facts: LandingFacts = {
          latest,
          runCounts:
            ppraRuns.status === "fulfilled" && punjabRuns.status === "fulfilled"
              ? { ppra: ppraRuns.value.runs.length, punjab: punjabRuns.value.runs.length }
              : null,
          listSizes,
        };
        // A failed load is retried on the next visit rather than cached.
        if (!facts.latest && !facts.runCounts) pending = null;
        return facts;
      },
    );
  return pending;
}
