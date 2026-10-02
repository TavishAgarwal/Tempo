import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function ConvergenceChart({ data }: { data: { t: number; cost: number }[] }) {
  const [table, setTable] = useState(false);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-muted">
        <span className="panel-title">Convergence · best cost J</span>
        <button className="font-mono text-[11px] uppercase tracking-wider text-primary underline-offset-2 hover:underline" onClick={() => setTable(!table)}>{table ? "Chart" : "Table"}</button>
      </div>
      {table ? (
        <table className="w-full font-mono text-xs"><thead><tr><th className="text-left">Seconds</th><th className="text-left">Cost J</th></tr></thead>
          <tbody>{data.slice(-12).map((d, i) => <tr key={i}><td>{d.t.toFixed(1)}</td><td>{d.cost.toFixed(4)}</td></tr>)}</tbody></table>
      ) : (
        <div className="h-40" role="img" aria-label="Convergence chart: best cost over time">
          <ResponsiveContainer>
            <LineChart data={data}><CartesianGrid stroke="var(--border)" strokeDasharray="2 4" />
              <XAxis dataKey="t" type="number" domain={[0, "auto"]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} stroke="var(--rule)" tickFormatter={(v: number) => `${v.toFixed(0)} s`} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} stroke="var(--rule)" tickFormatter={(v: number) => v.toFixed(3)} width={50} />
              <Tooltip contentStyle={{ background: "var(--raised)", border: "1px solid var(--rule)", borderRadius: 0, fontSize: 12 }} labelFormatter={(v) => `${Number(v).toFixed(1)} s`} formatter={(v) => [Number(v).toFixed(4), "Cost J"]} /><Line type="stepAfter" dataKey="cost" stroke="var(--primary)" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
