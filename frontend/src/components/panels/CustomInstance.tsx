import { pretty } from "../../lib";
import { useState } from "react";
import { api } from "../../api/client";
import { Button, Field } from "../ui/ui";
import { loadScenarios, selectScenario } from "../../state/actions";
import { useStore } from "../../state/store";

export interface Pt { lon: number; lat: number; demand: number }

/** Click-to-add / CSV upload of a custom instance. Map clicks arrive through `points`/`setPoints`. */
export default function CustomInstance({ adding, setAdding, depot, setDepot, points, setPoints }: {
  adding: "off" | "depot" | "customer"; setAdding: (m: "off" | "depot" | "customer") => void;
  depot: [number, number] | null; setDepot: (d: [number, number] | null) => void;
  points: Pt[]; setPoints: (p: Pt[]) => void;
}) {
  const [Q, setQ] = useState(30);
  const [K, setK] = useState(4);
  const [demand, setDemand] = useState(3);
  const [msg, setMsg] = useState<string | null>(null);
  const set = useStore((s) => s.set);

  const create = async () => {
    if (!depot || !points.length) { setMsg("Set a depot and add at least one customer first."); return; }
    try {
      const info = await api.createInstance({ depot_lon: depot[0], depot_lat: depot[1], customers: points.map((p) => ({ ...p, demand: p.demand || demand })), capacity: Q, n_vehicles: K, depart_s: 17.5 * 3600 });
      await loadScenarios();
      await selectScenario(info.name);
      setPoints([]); setDepot(null); setAdding("off"); setMsg(null);
      set({ toast: `Instance ${pretty(info.name)} created` });
    } catch (e) { setMsg((e as Error).message); }
  };

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    const rows = (await f.text()).split(/\r?\n/).map((l) => l.split(",").map((x) => x.trim())).filter((r) => r.length >= 2 && !isNaN(+r[0]));
    if (rows.length < 2) { setMsg("CSV format: the first row is the depot (lon, lat), then one customer per row (lon, lat, demand)."); return; }
    setDepot([+rows[0][0], +rows[0][1]]);
    setPoints(rows.slice(1).map((r) => ({ lon: +r[0], lat: +r[1], demand: Math.max(1, Math.round(+(r[2] ?? 1))) })));
    setMsg(`Loaded ${rows.length - 1} customers from the CSV file`);
  };

  return (
    <details className="border border-border bg-bg p-2.5">
      <summary className="panel-title cursor-pointer text-text">Custom instance</summary>
      <div className="mt-2 space-y-2">
        <div className="flex gap-1">
          <Button className="flex-1 text-xs" variant={adding === "depot" ? "primary" : "default"} onClick={() => setAdding(adding === "depot" ? "off" : "depot")}>Set depot</Button>
          <Button className="flex-1 text-xs" variant={adding === "customer" ? "primary" : "default"} onClick={() => setAdding(adding === "customer" ? "off" : "customer")}>Add customers</Button>
        </div>
        <p className="text-xs text-muted">{depot ? "Depot set" : "No depot yet"} · {points.length} {points.length === 1 ? "customer" : "customers"}</p>
        <div className="grid grid-cols-3 gap-1">
          <Field label="Demand"><input type="number" min={1} className="field" value={demand} onChange={(e) => { setDemand(+e.target.value); }} /></Field>
          <Field label="Capacity"><input type="number" min={1} className="field" value={Q} onChange={(e) => setQ(+e.target.value)} /></Field>
          <Field label="Vehicles"><input type="number" min={1} className="field" value={K} onChange={(e) => setK(+e.target.value)} /></Field>
        </div>
        <input type="file" accept=".csv" aria-label="Upload CSV" className="w-full text-xs text-muted file:mr-2 file:border file:border-rule file:bg-raised file:px-2 file:py-1 file:font-mono file:text-[11px] file:uppercase file:text-text" onChange={(e) => void onFile(e.target.files?.[0])} />
        <Button className="w-full" onClick={() => void create()}>Create instance</Button>
        {msg && <p role="alert" className="text-xs text-danger">{msg}</p>}
      </div>
    </details>
  );
}
