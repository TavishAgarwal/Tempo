import { KpiCard } from "../ui/ui";
import { km, num } from "../../lib";
import type { Plan } from "../../state/store";

export default function KpiStrip({ plan, base, Q, emissionsKg }: { plan: Plan | null; base?: Plan | null; Q: number; emissionsKg?: number | null }) {
  const m = plan?.metrics;
  const b = base?.metrics;
  const d = (k: string) => (m && b && num(b[k]) ? (100 * (num(m[k]) - num(b[k]))) / num(b[k]) : null);
  const loads = (m?.route_load as number[] | undefined) ?? [];
  const use = loads.length ? (100 * loads.reduce((a, c) => a + c, 0)) / (loads.length * Q) : 0;
  return (
    <div className="grid grid-cols-2 gap-2">
      <KpiCard label="Travel time" value={m ? (num(m.T) / 60).toFixed(1) : "–"} unit="min" delta={d("T")} />
      <KpiCard label="Distance" value={m ? km(num(m.D)).replace(" km", "") : "–"} unit="km" delta={d("D")} />
      <KpiCard label="Congestion exposure" value={m ? (num(m.C) / 60).toFixed(1) : "–"} unit="min" delta={d("C")} />
      <KpiCard label="Vehicles" value={m ? String(num(m.K)) : "–"} />
      {emissionsKg != null && <KpiCard label="CO₂ (illustrative)" value={emissionsKg.toFixed(1)} unit="kg" />}
      <KpiCard label="Load use" value={m ? use.toFixed(0) : "–"} unit="%" goodWhenDown={false} />
    </div>
  );
}
