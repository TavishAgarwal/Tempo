import type { components } from "./types";

export type S = components["schemas"];
const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch { /* keep status text */ }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export const api = {
  scenarios: () => req<S["ScenarioInfo"][]>("/scenarios"),
  scenario: (n: string) => req<S["InstanceDetail"]>(`/scenarios/${n}`),
  createInstance: (b: S["InstanceCreate"]) => req<S["ScenarioInfo"]>("/instances", { method: "POST", body: JSON.stringify(b) }),
  solve: (b: S["SolveRequest"]) => req<S["JobStatus"]>("/solve", { method: "POST", body: JSON.stringify(b) }),
  job: (id: string) => req<S["JobStatus"]>(`/jobs/${id}`),
  stop: (id: string) => req<{ stopping: boolean }>(`/jobs/${id}/stop`, { method: "POST" }),
  rescore: (id: string, depart: number) => req<S["RescoreOut"]>(`/jobs/${id}/rescore?depart=${depart}`, { method: "POST" }),
  incident: (b: S["IncidentRequest"]) => req<S["IncidentCreated"]>("/incidents", { method: "POST", body: JSON.stringify(b) }),
  path: (q: { from_lon: number; from_lat: number; to_lon: number; to_lat: number; depart: number }) =>
    req<S["PathOut"]>(`/paths?${new URLSearchParams(Object.entries(q).map(([k, v]) => [k, String(v)]))}`),
  congestion: (slot: number) => req<S["CongestionOut"]>(`/congestion?slot=${slot}`),
  live: () => req<S["LiveOut"]>("/live"),
  emissions: (id: string) => req<S["EmissionsOut"]>(`/jobs/${id}/emissions`),
  results: () => req<S["ResultTable"][]>("/results"),
};
