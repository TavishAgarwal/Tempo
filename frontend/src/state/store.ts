import { create } from "zustand";
import type { S } from "../api/client";
import type { StreamMsg } from "../api/ws";

export type Page = "landing" | "plan" | "incident" | "benchmark" | "path" | "about";
export type JobState = S["JobStatus"]["state"];

export interface Plan {
  routes: number[][];
  geometry: number[][][];
  metrics: Record<string, number | number[]>;
  depart: number;
}

interface Store {
  page: Page;
  scenarios: S["ScenarioInfo"][];
  scenario: string;
  detail: S["InstanceDetail"] | null;
  jobId: string | null;
  state: JobState;
  elapsed: number;
  plan: Plan | null;
  trace: { t: number; cost: number }[];
  error: string | null;
  offline: boolean;
  tilesOffline: boolean;
  emissions: S["EmissionsOut"] | null;
  toast: string | null;
  log: string[];
  logOpen: boolean;
  // incident
  incidentJobId: string | null;
  before: Plan | null;
  fallback: StreamMsg | null;
  vehicles: NonNullable<StreamMsg["vehicles"]>;
  blocked: number[];
  moved: NonNullable<StreamMsg["moved"]>;
  latency: number | null;
  reoptS: number | null;
  set: (p: Partial<Store>) => void;
}

export const useStore = create<Store>((set) => ({
  page: location.hash === "#app" ? "plan" : "landing", scenarios: [], scenario: "delhi_demo", detail: null, jobId: null, state: "idle",
  elapsed: 0, plan: null, trace: [], error: null, offline: false, tilesOffline: false, emissions: null, toast: null, log: [], logOpen: false,
  incidentJobId: null, before: null, fallback: null, vehicles: [], blocked: [], moved: [],
  latency: null, reoptS: null,
  set: (p) => set(p),
}));
