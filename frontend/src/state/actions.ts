import { api, type S } from "../api/client";
import { openStream, type StreamMsg } from "../api/ws";
import { useStore, type Plan } from "./store";

const set = useStore.getState().set;
const note = (t: string) => set({ log: [...useStore.getState().log.slice(-199), `${new Date().toLocaleTimeString()} ${t}`] });

export async function loadScenarios() {
  try {
    const list = await api.scenarios();
    set({ scenarios: list, offline: false });
    await selectScenario(list.find((s) => s.name === "delhi_demo")?.name ?? list[0]?.name ?? "");
  } catch {
    set({ offline: true });
  }
}

export async function selectScenario(name: string) {
  if (!name) return;
  set({ scenario: name, detail: null, plan: null, jobId: null, state: "idle", trace: [], error: null, before: null, fallback: null, vehicles: [], moved: [] });
  try {
    set({ detail: await api.scenario(name) });
  } catch (e) {
    set({ error: (e as Error).message, offline: true });
  }
}

function toPlan(m: StreamMsg, fallbackDepart: number): Plan | null {
  if (!m.routes || !m.metrics) return null;
  return { routes: m.routes, geometry: m.geometry ?? [], metrics: m.metrics, depart: m.depart ?? fallbackDepart };
}

export async function startSolve(req: S["SolveRequest"]) {
  set({ state: "solving", error: null, emissions: null, trace: [], plan: null, before: null, fallback: null, vehicles: [], moved: [], elapsed: 0 });
  try {
    const job = await api.solve(req);
    set({ jobId: job.job_id });
    const depart = req.depart_s ?? useStore.getState().detail?.depart_s ?? 0;
    openStream(job.job_id, (m) => {
      if (m.type === "improvement" && m.t !== undefined && m.cost !== undefined) {
        const st = useStore.getState();
        note(`improvement J=${m.cost.toFixed(4)} at ${m.t.toFixed(1)} s`);
        set({ trace: [...st.trace, { t: m.t, cost: m.cost }], elapsed: m.t, plan: toPlan(m, depart) ?? st.plan });
      } else if (m.type === "done") {
        note("plan ready");
        set({ state: "done", plan: toPlan(m, depart), toast: "Plan ready" });
        api.emissions(job.job_id).then((emissions) => set({ emissions })).catch(() => set({ emissions: null }));
      } else if (m.type === "error") {
        set({ state: "error", error: m.message ?? "Solve failed" });
      }
    });
  } catch (e) {
    set({ state: "error", error: (e as Error).message });
  }
}

export async function stopSolve() {
  const id = useStore.getState().jobId;
  if (id) await api.stop(id);
}

export async function simulateIncident(req: Omit<S["IncidentRequest"], "job_id">) {
  const st = useStore.getState();
  if (!st.jobId || !st.plan) return;
  set({ before: st.plan, state: "solving", fallback: null, vehicles: [], moved: [], latency: null, reoptS: null, error: null, trace: [] });
  try {
    const inc = await api.incident({ ...req, job_id: st.jobId });
    set({ incidentJobId: inc.job_id });
    const depart = st.plan.depart;
    openStream(inc.job_id, (m) => {
      if (m.type === "fallback") {
        note(`safe plan in ${((m.latency_s ?? 0) * 1000).toFixed(0)} ms`);
        set({ state: "safe_plan", fallback: m, vehicles: m.vehicles ?? [], latency: m.latency_s ?? null, plan: toPlan(m, depart) });
      } else if (m.type === "improvement") {
        const s2 = useStore.getState();
        set({ state: "optimising", elapsed: m.t ?? 0, trace: [...s2.trace, { t: m.t ?? 0, cost: m.cost ?? 0 }],
          plan: s2.plan ? { ...s2.plan, routes: m.routes ?? s2.plan.routes, geometry: m.geometry ?? s2.plan.geometry } : s2.plan });
      } else if (m.type === "done") {
        set({ state: "done", plan: toPlan(m, depart), moved: m.moved ?? [], reoptS: m.reopt_s ?? null,
          toast: `Re-optimised in ${(m.reopt_s ?? 0).toFixed(1)} s` });
      } else if (m.type === "error") {
        set({ state: "error", error: m.message ?? "Incident failed" });
      }
    });
  } catch (e) {
    set({ state: "error", error: (e as Error).message });
  }
}
