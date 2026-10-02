import { routeColor } from "../../lib";
import type { Plan } from "../../state/store";

export default function RouteList({ plan, Q, demand }: { plan: Plan | null; Q: number; demand: number[] }) {
  if (!plan) return <p className="text-sm text-muted">No plan yet. Press Solve to build one.</p>;
  const rt = (plan.metrics.route_T as number[] | undefined) ?? [];
  return (
    <ul className="space-y-1">
      {plan.routes.filter((r) => r.length).map((r, i) => {
        const load = r.reduce((a, c) => a + (demand[c] ?? 0), 0), pct = Math.min(100, (100 * load) / Q);
        return (
          <li key={i} className="grid grid-cols-[14px_auto_1fr_auto] items-center gap-x-2 border border-border bg-bg py-1.5 pl-0 pr-2 font-mono text-xs" style={{ borderLeft: `4px solid ${routeColor(i)}` }}>
            <span />
            <span className="w-9 text-text">V{String(i + 1).padStart(2, "0")}</span>
            <span className="relative h-2 bg-border" title={`load ${load}/${Q}`}><span className="absolute inset-y-0 left-0" style={{ width: `${pct}%`, background: routeColor(i) }} /></span>
            <span className="text-right text-muted"><b className="font-medium text-text">{r.length}</b> stops · {load}/{Q} · <b className="font-medium text-text">{rt[i] ? (rt[i] / 60).toFixed(0) : "–"}</b> min</span>
          </li>
        );
      })}
    </ul>
  );
}
