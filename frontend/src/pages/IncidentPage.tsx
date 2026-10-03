import { useEffect, useMemo, useState } from "react";
import { api, type S } from "../api/client";
import ConvergenceChart from "../components/charts/ConvergenceChart";
import MapView, { CongestionLayer, IncidentLayer, RouteLayer, VehicleMarker } from "../components/map/MapView";
import KpiStrip from "../components/panels/KpiStrip";
import { Button, Field, StatusBadge } from "../components/ui/ui";
import Shell from "../components/ui/Shell";
import { hhmm, num } from "../lib";
import { simulateIncident } from "../state/actions";
import { useStore } from "../state/store";

export default function IncidentPage() {
  const st = useStore();
  const picking = true;
  const [roads, setRoads] = useState<S["CongestionEdge"][]>([]);
  const [picked, setPicked] = useState<number[]>([]); // directed edge ids; a click closes both directions
  const [severity, setSeverity] = useState(0.1);
  const [startH, setStartH] = useState(18);
  const [durH, setDurH] = useState(1);
  const [mu, setMu] = useState(0);
  const [hover, setHover] = useState(-1);
  const [ghost, setGhost] = useState(true);

  useEffect(() => { api.congestion(70).then((c) => setRoads(c.edges)).catch(() => setRoads([])); }, []);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") setPicked([]); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  // Directed edge id -> id of the opposite direction of the same road (if any).
  const reverse = useMemo(() => {
    const key = (a: [number, number], b: [number, number]) => `${a[0]},${a[1]}|${b[0]},${b[1]}`;
    const at = new Map(roads.map((r, i) => [key(r.a, r.b), i]));
    return roads.map((r) => at.get(key(r.b, r.a)));
  }, [roads]);

  const nearest = (lon: number, lat: number): number => {
    if (!roads.length) return -1;
    const k = Math.cos((lat * Math.PI) / 180);
    let best = -1, bd = Infinity;
    roads.forEach((r, i) => {
      const ax = r.a[0] * k, ay = r.a[1], bx = r.b[0] * k, by = r.b[1], px = lon * k;
      const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
      const t = L2 ? Math.max(0, Math.min(1, ((px - ax) * dx + (lat - ay) * dy) / L2)) : 0;
      const d = Math.hypot(px - (ax + t * dx), lat - (ay + t * dy));
      if (d < bd) { bd = d; best = i; }
    });
    return bd > 0.0005 ? -1 : best; // ~50 m: ignore points far from any road
  };

  const pickRoad = (lon: number, lat: number) => {
    const best = nearest(lon, lat);
    if (best < 0) return;
    const ids = [best, ...(reverse[best] !== undefined ? [reverse[best] as number] : [])];
    setPicked((p) => (p.includes(best) ? p.filter((e) => !ids.includes(e)) : [...p, ...ids.filter((e) => !p.includes(e))]));
  };

  // The incident must start while the plan is running; after every vehicle is back there is nothing left to re-plan.
  const departH = ((st.before ?? st.plan)?.depart ?? 17.5 * 3600) / 3600;
  const startMin = Math.floor(departH * 4) / 4, startMax = Math.min(24, startMin + 4);
  useEffect(() => { setStartH(Math.min(startMax, Math.ceil((startMin + 0.5) * 4) / 4)); }, [startMin, startMax]);
  const empty = st.state === "done" && !!st.fallback?.metrics && num(st.fallback.metrics.T) === 0 && num(st.plan?.metrics?.T) === 0;

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
        <p className="text-sm">Solve a plan on the Plan page first, then click the roads to close on the map.</p>
        <p className="text-xs text-muted">{roads.length ? "Click a road on the map to close it; click it again to reopen. Click several roads to close a longer stretch." : "Loading the road network…"}</p>
        <div className="flex gap-1">
          <p className="flex-1 self-center text-sm">{picked.length ? `${new Set(picked.map((e) => Math.min(e, reverse[e] ?? e))).size} road segment(s) closed` : "No roads selected yet"}</p>
          <Button className="text-xs" disabled={!picked.length} onClick={() => setPicked([])}>Clear (Esc)</Button>
        </div>
        <Field label="Severity (speed factor)"><div className="flex gap-1">
          <Button variant={severity === 0.1 ? "primary" : "default"} className="flex-1 text-xs" onClick={() => setSeverity(0.1)}>Blocked · 0.1</Button>
          <Button variant={severity === 0.4 ? "primary" : "default"} className="flex-1 text-xs" onClick={() => setSeverity(0.4)}>Heavy · 0.4</Button></div></Field>
        <Field label={`Custom speed factor: ${severity}`}><input type="range" min={0.05} max={1} step={0.05} value={severity} onChange={(e) => setSeverity(+e.target.value)} className="w-full" /></Field>
        <Field label={`Incident start: ${hhmm(startH * 3600)}`}><input type="range" min={startMin} max={startMax} step={0.25} value={startH} onChange={(e) => setStartH(+e.target.value)} className="w-full" /></Field>
        <Field label={`Duration: ${durH} h`}><input type="range" min={0.25} max={4} step={0.25} value={durH} onChange={(e) => setDurH(+e.target.value)} className="w-full" /></Field>
        <Field label={`Stability vs quality (μ = ${mu})`}><input type="range" min={0} max={0.05} step={0.005} value={mu} onChange={(e) => setMu(+e.target.value)} className="w-full" /></Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={ghost} onChange={(e) => setGhost(e.target.checked)} />Show the previous plan</label>
        <Button variant="danger" className="w-full border-2" disabled={!ready || !picked.length || busy}
          onClick={() => void simulateIncident({ edges: picked, factor: severity, t_start: startH * 3600, t_end: (startH + durH) * 3600, budget_s: 10, mu, seed: 0 })}>Simulate incident</Button>
        {st.error && <p role="alert" className="text-sm text-danger">{st.error}</p>}
      </>}
      right={<>
        <div className="flex items-center justify-between"><h2 className="panel-title text-text">Incident response</h2>
          <StatusBadge state={st.state} extra={st.state === "optimising" ? `${st.elapsed.toFixed(1)} s` : st.state === "done" && st.reoptS ? `in ${st.reoptS.toFixed(1)} s` : undefined} /></div>
        {empty && <p role="alert" className="text-sm text-warning">All vehicles had already finished before {hhmm(startH * 3600)}, so there was nothing to re-plan. Choose an earlier incident start time (the plan departs at {hhmm(departH * 3600)}).</p>}
        {st.latency != null && <p className="text-sm">Safe plan ready in <span className="font-mono text-primary">{(st.latency * 1000).toFixed(0)} ms</span>.</p>}
        <div className="grid grid-cols-3 gap-1 text-xs"><div /><div className="panel-title">Safe plan</div><div className="panel-title">Re-optimised</div>
          <div>Travel time</div><div className="font-mono">{fb ? (num(fb.T) / 60).toFixed(1) : "–"} min</div><div className="font-mono">{fin ? (num(fin.T) / 60).toFixed(1) : "–"} min</div>
          <div>Congestion</div><div className="font-mono">{fb ? (num(fb.C) / 60).toFixed(1) : "–"} min</div><div className="font-mono">{fin ? (num(fin.C) / 60).toFixed(1) : "–"} min</div></div>
        <KpiStrip plan={st.plan} base={fbPlan} Q={st.detail?.capacity ?? 1} />
        <div><h3 className="panel-title">Customers moved ({st.moved.length})</h3>
          <ul className="max-h-32 overflow-y-auto font-mono text-xs">{st.moved.map((m) => <li key={m.customer}>Customer {m.customer}: V{String(m.from + 1).padStart(2, "0")} → V{String(m.to + 1).padStart(2, "0")}</li>)}</ul></div>
        <ConvergenceChart data={st.trace} />
      </>}>
      
        <MapView onClick={pickRoad} onHover={(p) => setHover(p ? nearest(p[0], p[1]) : -1)}>
          {ghost && st.before && <RouteLayer geometry={st.before.geometry} ghost />}
          {st.plan && <RouteLayer geometry={st.plan.geometry} dashed={st.state === "safe_plan"} />}
          {picking && <CongestionLayer edges={roads} faint />}
          {hover >= 0 && !picked.includes(hover) && <IncidentLayer edges={[[roads[hover].a, roads[hover].b]]} hover />}
          {picked.length > 0 && <IncidentLayer edges={picked.map((e) => [roads[e].a, roads[e].b])} />}
          {st.vehicles.map((v) => <VehicleMarker key={v.vehicle} lon={v.lon} lat={v.lat} label={`V${v.vehicle + 1}`} eta={v.eta_s} />)}
        </MapView>
      
    </Shell>
  );
}
