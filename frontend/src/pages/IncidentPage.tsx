import { useEffect, useState } from "react";
import ConvergenceChart from "../components/charts/ConvergenceChart";
import MapView, { IncidentLayer, RouteLayer, VehicleMarker } from "../components/map/MapView";
import KpiStrip from "../components/panels/KpiStrip";
import { Button, Field, StatusBadge } from "../components/ui/ui";
import Shell from "../components/ui/Shell";
import { hhmm, num } from "../lib";
import { simulateIncident } from "../state/actions";
import { useStore } from "../state/store";

export default function IncidentPage() {
  const st = useStore();
  const [drawing, setDrawing] = useState(false);
  const [poly, setPoly] = useState<[number, number][]>([]);
  const [severity, setSeverity] = useState(0.1);
  const [startH, setStartH] = useState(18);
  const [durH, setDurH] = useState(1);
  const [mu, setMu] = useState(0);
  const [ghost, setGhost] = useState(true);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "i" || e.key === "I") { setDrawing(true); setPoly([]); }
      if (e.key === "Escape") { setDrawing(false); setPoly([]); }
      if (e.key === "Enter" && drawing && poly.length >= 3) setDrawing(false);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [drawing, poly.length]);

  const busy = st.state === "solving" || st.state === "optimising";
  const ready = !!st.before || (st.plan && st.jobId);
  const fb = st.fallback?.metrics;
  const fin = st.plan?.metrics;
  const fbPlan = st.fallback && st.fallback.routes && st.fallback.metrics
    ? { routes: st.fallback.routes, geometry: st.fallback.geometry ?? [], metrics: st.fallback.metrics, depart: 0 }
    : null;

  return (
    <Shell rightTitle="Incident response"
      left={<>
        <p className="text-sm">Solve a plan on the Plan page first, then draw the blocked area on the map.</p>
        <Button onClick={() => { setDrawing(true); setPoly([]); }} variant={drawing ? "primary" : "default"} className="w-full">Draw blocked area (I)</Button>
        <p className="text-xs text-muted">{drawing ? "Click the map to add corners. Press Enter to finish or Esc to cancel." : poly.length ? `${poly.length} corners drawn` : "No area drawn yet"}</p>
        <Field label="Severity (speed factor)"><div className="flex gap-1">
          <Button variant={severity === 0.1 ? "primary" : "default"} className="flex-1 text-xs" onClick={() => setSeverity(0.1)}>Blocked · 0.1</Button>
          <Button variant={severity === 0.4 ? "primary" : "default"} className="flex-1 text-xs" onClick={() => setSeverity(0.4)}>Heavy · 0.4</Button></div></Field>
        <Field label={`Custom speed factor: ${severity}`}><input type="range" min={0.05} max={1} step={0.05} value={severity} onChange={(e) => setSeverity(+e.target.value)} className="w-full" /></Field>
        <Field label={`Incident start: ${hhmm(startH * 3600)}`}><input type="range" min={6} max={22} step={0.25} value={startH} onChange={(e) => setStartH(+e.target.value)} className="w-full" /></Field>
        <Field label={`Duration: ${durH} h`}><input type="range" min={0.25} max={4} step={0.25} value={durH} onChange={(e) => setDurH(+e.target.value)} className="w-full" /></Field>
        <Field label={`Stability vs quality (μ = ${mu})`}><input type="range" min={0} max={0.05} step={0.005} value={mu} onChange={(e) => setMu(+e.target.value)} className="w-full" /></Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={ghost} onChange={(e) => setGhost(e.target.checked)} />Show the previous plan</label>
        <Button variant="danger" className="w-full border-2" disabled={!ready || poly.length < 3 || busy}
          onClick={() => void simulateIncident({ polygon: poly, factor: severity, t_start: startH * 3600, t_end: (startH + durH) * 3600, budget_s: 10, mu, seed: 0 })}>Simulate incident</Button>
        {st.error && <p role="alert" className="text-sm text-danger">{st.error}</p>}
      </>}
      right={<>
        <div className="flex items-center justify-between"><h2 className="panel-title text-text">Incident response</h2>
          <StatusBadge state={st.state} extra={st.state === "optimising" ? `${st.elapsed.toFixed(1)} s` : st.state === "done" && st.reoptS ? `in ${st.reoptS.toFixed(1)} s` : undefined} /></div>
        {st.latency != null && <p className="text-sm">Safe plan ready in <span className="font-mono text-primary">{(st.latency * 1000).toFixed(0)} ms</span>.</p>}
        <div className="grid grid-cols-3 gap-1 text-xs"><div /><div className="panel-title">Safe plan</div><div className="panel-title">Re-optimised</div>
          <div>Travel time</div><div className="font-mono">{fb ? (num(fb.T) / 60).toFixed(1) : "–"} min</div><div className="font-mono">{fin ? (num(fin.T) / 60).toFixed(1) : "–"} min</div>
          <div>Congestion</div><div className="font-mono">{fb ? (num(fb.C) / 60).toFixed(1) : "–"} min</div><div className="font-mono">{fin ? (num(fin.C) / 60).toFixed(1) : "–"} min</div></div>
        <KpiStrip plan={st.plan} base={fbPlan} Q={st.detail?.capacity ?? 1} />
        <div><h3 className="panel-title">Customers moved ({st.moved.length})</h3>
          <ul className="max-h-32 overflow-y-auto font-mono text-xs">{st.moved.map((m) => <li key={m.customer}>Customer {m.customer}: V{String(m.from + 1).padStart(2, "0")} → V{String(m.to + 1).padStart(2, "0")}</li>)}</ul></div>
        <ConvergenceChart data={st.trace} />
      </>}>
      
        <MapView onClick={(lon, lat) => drawing && setPoly((p) => [...p, [lon, lat]])}>
          {ghost && st.before && <RouteLayer geometry={st.before.geometry} ghost />}
          {st.plan && <RouteLayer geometry={st.plan.geometry} dashed={st.state === "safe_plan"} />}
          {poly.length > 1 && <IncidentLayer edges={[[...poly, poly[0]]]} />}
          {st.vehicles.map((v) => <VehicleMarker key={v.vehicle} lon={v.lon} lat={v.lat} label={`V${v.vehicle + 1}`} eta={v.eta_s} />)}
        </MapView>
      
    </Shell>
  );
}
