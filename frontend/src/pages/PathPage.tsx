import { useState } from "react";
import { api, type S } from "../api/client";
import MapView from "../components/map/MapView";
import { Button, Field } from "../components/ui/ui";
import { hhmm, km, min } from "../lib";
import { Polyline, CircleMarker } from "react-leaflet";

export default function PathPage() {
  const [pts, setPts] = useState<[number, number][]>([]);
  const [dep, setDep] = useState(18 * 60);
  const [out, setOut] = useState<S["PathOut"] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const click = async (lon: number, lat: number) => {
    const next = pts.length >= 2 ? [[lon, lat] as [number, number]] : [...pts, [lon, lat] as [number, number]];
    setPts(next);
    setOut(null);
    if (next.length === 2) await query(next, dep);
  };
  const query = async (p: [number, number][], d: number) => {
    try {
      setErr(null);
      setOut(await api.path({ from_lon: p[0][0], from_lat: p[0][1], to_lon: p[1][0], to_lat: p[1][1], depart: d * 60 }));
    } catch (e) { setErr((e as Error).message); }
  };
  return (
    <div className="flex h-full flex-col overflow-y-auto lg:flex-row lg:overflow-visible">
      <aside className="w-full shrink-0 space-y-4 border-b border-border bg-surface p-4 lg:w-80 lg:border-b-0 lg:border-r">
        <p className="text-sm">Click the map to set an origin, then a destination.</p>
        <Field label={`Departure time: ${hhmm(dep * 60)}`}><input type="range" min={0} max={1425} step={15} value={dep} className="w-full"
          onChange={(e) => { setDep(+e.target.value); if (pts.length === 2) void query(pts, +e.target.value); }} /></Field>
        <Button onClick={() => { setPts([]); setOut(null); }}>Clear points</Button>
        {err && <p role="alert" className="text-sm text-danger">{err}</p>}
        {out && <div className="space-y-1 font-mono text-sm">
          <div>Time-aware fastest: {min(out.travel_s)} · {km(out.distance_m)}</div>
          <div>Free-flow route in traffic: {min(out.free_flow_travel_s)}</div>
          <div className="text-success">Time saved: {min(Math.max(0, out.free_flow_travel_s - out.travel_s))}</div></div>}
        <p className="text-xs text-muted">Speed source: calibrated time-of-day profile (synthetic).</p>
      </aside>
      <main className="min-h-[320px] min-w-0 flex-1">
        <MapView onClick={(lon, lat) => void click(lon, lat)}>
          {out && <Polyline positions={out.free_flow_geometry.map(([x, y]) => [y, x])} pathOptions={{ color: "#8f8d7c", weight: 4, dashArray: "6 6" }} />}
          {out && <Polyline positions={out.geometry.map(([x, y]) => [y, x])} pathOptions={{ color: "#b8f04a", weight: 5 }} />}
          {pts.map((p, i) => <CircleMarker key={i} center={[p[1], p[0]]} radius={7} pathOptions={{ color: i ? "#ff4d3d" : "#f0b429" }} />)}
        </MapView>
      </main>
    </div>
  );
}
