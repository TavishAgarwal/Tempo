import { useEffect, useState } from "react";
import { api, type S } from "../api/client";
import { Button } from "../components/ui/ui";
import { humanize } from "../lib";

const TAKEAWAY: Record<string, string> = {
  e1: "How close the solver gets to proven optima and best-known solutions.",
  e2: "QPSO against PSO, GA and random restart at equal wall-clock budget; every result is reported, wins and losses.",
  e3: "Realised travel time when planning with time-of-day speeds versus free-flow speeds.",
  e4: "Fallback latency and quality after an incident against the baselines B0–B3.",
  e5: "Runtime and memory against the number of customers.",
};

function fmt(v: unknown, key = ""): string {
  if (/^(feasible|valid)$/i.test(key) && (v === 0 || v === 1 || typeof v === "boolean")) return v ? "Yes" : "No";
  if (v == null) return "–";
  if (typeof v === "number") return String(Number(v.toFixed(3)));
  return String(v);
}

export default function BenchmarkPage() {
  const [res, setRes] = useState<S["ResultTable"][]>([]);
  const [tab, setTab] = useState("");
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.results().then((r) => { setRes(r); setTab(r[0]?.experiment ?? ""); }).catch((e: Error) => setErr(e.message)); }, []);
  const cur = res.find((r) => r.experiment === tab);
  const cols = cur?.rows[0] ? Object.keys(cur.rows[0]) : [];
  return (
    <div className="h-full overflow-y-auto p-4">
      <div role="tablist" className="mb-3 flex flex-wrap gap-1">
        {res.map((r) => <Button key={r.experiment} role="tab" variant={tab === r.experiment ? "primary" : "default"} onClick={() => setTab(r.experiment)}>{r.title}</Button>)}
      </div>
      {err && <p className="text-danger">{err}</p>}
      {!res.length && !err && <p className="text-muted">No saved results yet. Run <code className="font-mono text-text">make exp-all</code> to generate them.</p>}
      {cur && (
        <section>
          <p className="mb-3 max-w-3xl text-sm leading-relaxed">{TAKEAWAY[cur.experiment]}</p>
          <div className="overflow-x-auto"><table className="min-w-full font-mono text-xs">
            <thead><tr>{cols.map((c) => <th key={c} className="whitespace-nowrap border-b border-rule px-2 py-1.5 text-left font-medium uppercase tracking-wider text-muted">{humanize(c)}</th>)}</tr></thead>
            <tbody>{cur.rows.map((r, i) => <tr key={i} className="hover:bg-raised">{cols.map((c) => <td key={c} className="border-b border-border px-2 py-1.5">{fmt(r[c], c)}</td>)}</tr>)}</tbody>
          </table></div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {cur.files.filter((f) => f.endsWith(".png")).map((f) => (
              <figure key={f}><img alt={f} src={`/api/results/${cur.experiment}/${f}`} className="w-full border border-border bg-white" />
                <figcaption className="mt-1 flex justify-between text-xs text-muted"><span className="font-mono">{f}</span>
                  <a className="text-primary underline-offset-2 hover:underline" href={`/api/results/${cur.experiment}/${f}`} download>Download PNG</a></figcaption></figure>))}
          </div>
          <a className="mt-3 inline-block text-sm text-primary underline-offset-2 hover:underline" href={`/api/results/${cur.experiment}/table.csv`} download>Download CSV</a>
        </section>
      )}
    </div>
  );
}
