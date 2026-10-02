export const ROUTE_COLORS = ["#b8f04a", "#f0b429", "#ff6a45", "#f27fc4", "#4fd1b0", "#b79cff", "#e6e3d3", "#d4a373"];
export const routeColor = (i: number) => ROUTE_COLORS[i % 8];
export const routeDash = (i: number) => (i >= 8 ? "6 6" : undefined);
export const min = (s: number) => `${(s / 60).toFixed(1)} min`;
export const km = (m: number) => `${(m / 1000).toFixed(1)} km`;
export const hhmm = (s: number) => {
  const h = Math.floor(s / 3600) % 24;
  const m = Math.floor((s % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
};
export const congColor = (ratio: number) =>
  ratio >= 0.8 ? "#b8f04a" : ratio >= 0.6 ? "#f0b429" : ratio >= 0.4 ? "#ff9f43" : "#ff4d3d";
export const num = (v: unknown): number => (typeof v === "number" ? v : 0);

/** "delhi_demo" -> "Delhi demo" */
export const pretty = (name: string) => { const s = name.replace(/[_-]+/g, " ").trim(); return s ? s[0].toUpperCase() + s.slice(1) : s; };
const ACRONYMS: Record<string, string> = { j: "J", t: "T", d: "D", c: "C", k: "K", qpso: "QPSO", pso: "PSO", ga: "GA", vnd: "VND", pyvrp: "PyVRP", cpu: "CPU", mb: "MB", rss: "RSS", ci: "CI", p: "p", id: "ID", n: "n", bks: "BKS", milp: "MILP", mu: "μ" };
const LABELS: Record<string, string> = { t: "Travel time T", d: "Distance D", c: "Congestion C", j: "Cost J", n: "Customers n" };
/** "runtime_s" -> "Runtime (s)", "j_mean" -> "J mean" */
export const humanize = (key: string) => {
  if (LABELS[key.toLowerCase()]) return LABELS[key.toLowerCase()];
  const m = /^(.*?)_(s|ms|min|km|kg|mb|pct)$/.exec(key);
  const unit = m ? (m[2] === "pct" ? "%" : m[2] === "mb" ? "MB" : m[2]) : "";
  const words = (m ? m[1] : key).split(/[_\s]+/).filter(Boolean).map((w, i) => ACRONYMS[w.toLowerCase()] ?? (i === 0 ? w[0].toUpperCase() + w.slice(1) : w));
  return words.join(" ") + (unit ? ` (${unit})` : "");
};
