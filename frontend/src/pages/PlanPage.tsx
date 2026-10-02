import { useEffect, useState } from "react";
import { api, type S } from "../api/client";
import ConvergenceChart from "../components/charts/ConvergenceChart";
import MapView, { CongestionLayer, RouteLayer, PointMarkers } from "../components/map/MapView";
import CustomInstance, { type Pt } from "../components/panels/CustomInstance";
import KpiStrip from "../components/panels/KpiStrip";
import RouteList from "../components/panels/RouteList";
import { Button, Field, Select, StatusBadge } from "../components/ui/ui";
import Shell from "../components/ui/Shell";
import { hhmm, pretty } from "../lib";
import { selectScenario, startSolve, stopSolve } from "../state/actions";
import { useStore } from "../state/store";

export default function PlanPage() {
  const st = useStore();
  const [preset, setPreset] = useState<S["SolveRequest"]["preset"]>("fastest");
  const [solver, setSolver] = useState<S["SolveRequest"]["solver"]>("qpso");
  const [budget, setBudget] = useState(10);
  const [seed, setSeed] = useState(0);
  const [slotMin, setSlotMin] = useState(17.5 * 60);
  const [cong, setCong] = useState<S["CongestionOut"] | null>(null);
  const [showCong, setShowCong] = useState(true);
  const [adding, setAdding] = useState<"off" | "depot" | "customer">("off");
  const [depot, setDepot] = useState<[number, number] | null>(null);
  const [points, setPoints] = useState<Pt[]>([]);
  const [live, setLive] = useState(false);
  const [liveInfo, setLiveInfo] = useState<S["LiveOut"] | null>(null);
  useEffect(() => { api.live().then(setLiveInfo).catch(() => setLiveInfo(null)); }, []);
  const solving = st.state === "solving";
  const demand = [0, ...(st.detail?.customers.map((c) => c.demand) ?? [])];

  useEffect(() => {
    if (!showCong) return;
    const slot = Math.floor(slotMin / 15) % 96;
    api.congestion(slot).then(setCong).catch(() => setCong(null));
  }, [slotMin, showCong]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !(e.target instanceof HTMLInputElement) && !solving) void run();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  });

  const run = () => startSolve({ instance_id: st.scenario, solver, preset, budget_s: budget, seed, depart_s: slotMin * 60, live: live && !!liveInfo?.available });

  const rescore = async (min: number) => {
    setSlotMin(min);
    if (st.jobId && st.plan && st.state === "done") {
      const r = await api.rescore(st.jobId, min * 60);
      st.set({ plan: { ...st.plan, metrics: { ...st.plan.metrics, ...r.metrics } as never, depart: min * 60 } });
    }
  };

  return (
    <Shell rightTitle="Plan"
      left={<>
        <Field label="Scenario">
          <Select label="Scenario" value={st.scenario} onChange={(v) => void selectScenario(v)} options={st.scenarios.map((s) => ({ value: s.name, label: pretty(s.name), hint: `${s.n_customers} stops` }))} />
        </Field>
        <p className="text-xs text-muted">{st.detail ? `${st.detail.n_customers} customers · ${st.detail.n_vehicles ?? "unlimited"} vehicles · capacity ${st.detail.capacity} per vehicle` : "Preparing the road network. The first run takes about 10 s."}</p>
        <Field label="Priority preset">
          <div className="flex gap-1">{(["fastest", "balanced", "low_congestion"] as const).map((p) => (
            <Button key={p} variant={preset === p ? "primary" : "default"} onClick={() => setPreset(p)} className="flex-1 px-1 text-xs">{p === "low_congestion" ? "Low congestion" : p[0].toUpperCase() + p.slice(1)}</Button>))}</div>
        </Field>
        <Field label="Solver">
          <Select label="Solver" value={solver} onChange={setSolver} options={[
            { value: "qpso", label: "TA-QPSO", hint: "default" }, { value: "pso", label: "PSO" }, { value: "ga", label: "Genetic algorithm" },
            { value: "random", label: "Random restart" }, { value: "pyvrp", label: "PyVRP", hint: "baseline" }]} />
        </Field>
        {solver === "qpso" && <p className="-mt-2 text-xs text-muted">Quantum-inspired, but runs on a normal CPU.</p>}
        <Field label={`Time budget: ${budget} s`}><input type="range" min={10} max={120} step={5} value={budget} onChange={(e) => setBudget(+e.target.value)} className="w-full" /></Field>
        <Field label="Random seed"><input type="number" className="field" value={seed} onChange={(e) => setSeed(+e.target.value)} /></Field>
        <Field label={`Departure time: ${hhmm(slotMin * 60)}`}>
          <input type="range" min={360} max={1320} step={15} value={slotMin} onChange={(e) => void rescore(+e.target.value)} className="w-full" aria-label="Time of day" />
        </Field>
        {liveInfo?.available && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />Live traffic (TomTom){live && <span className="text-xs text-muted"> · {liveInfo.fetched_at?.slice(11, 16)}</span>}</label>}
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showCong} onChange={(e) => setShowCong(e.target.checked)} />Congestion layer</label>
        <CustomInstance adding={adding} setAdding={setAdding} depot={depot} setDepot={setDepot} points={points} setPoints={setPoints} />
        {solving ? <Button variant="danger" className="w-full" onClick={() => void stopSolve()}>Stop</Button> : <Button variant="primary" className="w-full" disabled={!st.detail} onClick={() => void run()}>Solve</Button>}
        {st.error && <p role="alert" className="text-sm text-danger">{st.error}</p>}
        <p className="border-t border-border pt-3 text-xs leading-relaxed text-muted">Speed source: {live ? "live traffic (TomTom) overlaid on the calibrated profile" : "calibrated time-of-day profile (synthetic)"}.<br />Congestion exposure is the time spent on roads running below 50% of free-flow speed.</p>
      </>}
      right={<>
        <div className="flex items-center justify-between"><h2 className="panel-title text-text">Plan</h2><StatusBadge state={st.state} extra={solving ? `${st.elapsed.toFixed(1)} s` : undefined} /></div>
        <KpiStrip plan={st.plan} Q={st.detail?.capacity ?? 1} emissionsKg={st.emissions?.kg ?? null} />
        <RouteList plan={st.plan} Q={st.detail?.capacity ?? 1} demand={demand} />
        <ConvergenceChart data={st.trace} />
      </>}>
      
        <MapView onClick={(lon, lat) => {
          if (adding === "depot") setDepot([lon, lat]);
          else if (adding === "customer") setPoints((p) => [...p, { lon, lat, demand: 0 }]);
        }}>
          <PointMarkers depot={depot} points={points} />
          {showCong && cong && <CongestionLayer edges={cong.edges} />}
          {st.plan && <RouteLayer geometry={st.plan.geometry} />}
        </MapView>
      
    </Shell>
  );
}
