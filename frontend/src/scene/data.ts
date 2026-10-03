/** Loads the real Delhi demo (public/landing-data.json) and projects it into scene units (1 unit = 100 m). */

export type V2 = [number, number];

interface Raw {
  source: string;
  nodes: V2[];
  edges: [number, number, number, number][];
  ratios: { peak: Record<string, number>; night: Record<string, number> };
  hourly: Record<string, number[]>;
  depot: V2;
  customers: [number, number, number, number][];
  capacity: number;
  plan: { routes: number[][]; geometry: V2[][]; T_min: number; D_km: number; C_min: number; J: number };
  incident: {
    t_start_h: number; t_end_h: number; factor: number; segments: [V2, V2][];
    fallback_latency_s: number;
    fallback: { T_rem_min: number; J: number }; final: { T_rem_min: number; J: number };
    vehicles: { v: number; status: string; lon: number; lat: number }[];
    moved: { customer: number; from: number; to: number }[];
    geometry: V2[][]; fallback_geometry: V2[][];
  };
}

export interface Block { x: number; z: number; w: number; d: number; h: number; c: string }

export interface SceneData {
  source: string;
  bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  blocks: Block[];
  nodes: V2[]; // scene xz
  edges: [number, number, number, number][]; // a, b, class, peak ratio
  ratioPeak: Record<string, number>;
  hourly: Record<string, number[]>; // mean speed ratio per hour of day, by road class
  depot: V2;
  customers: { p: V2; demand: number; vehicle: number }[];
  capacity: number;
  routes: V2[][];
  plan: Raw["plan"];
  incident: {
    segments: [V2, V2][]; centre: V2; radius: number;
    vehicles: { v: number; p: V2; status: string }[];
    moved: { customer: number; from: number; to: number; p: V2 }[];
    routes: V2[][];
    fallbackLatencyS: number;
    fallback: Raw["incident"]["fallback"]; final: Raw["incident"]["final"];
    tStartH: number; tEndH: number;
  };
  busiest: V2; // mid-point of the busiest arterial edge
  stopOnRoute3: V2;
}

let cache: Promise<SceneData> | null = null;
export const loadLanding = (): Promise<SceneData> => (cache ??= fetch("/landing-data.json").then((r) => r.json() as Promise<Raw>).then(project));

function project(raw: Raw): SceneData {
  const xs = raw.nodes.map((n) => n[0]), ys = raw.nodes.map((n) => n[1]);
  const lon0 = (Math.min(...xs) + Math.max(...xs)) / 2, lat0 = (Math.min(...ys) + Math.max(...ys)) / 2;
  const kx = (Math.cos((lat0 * Math.PI) / 180) * 111320) / 100, kz = 110574 / 100;
  const P = (q: V2): V2 => [(q[0] - lon0) * kx, -(q[1] - lat0) * kz];
  const nodes = raw.nodes.map(P);
  const segs = raw.incident.segments.map(([a, b]) => [P(a), P(b)] as [V2, V2]);
  const mid = segs.map(([a, b]): V2 => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
  const centre: V2 = [mid.reduce((s, m) => s + m[0], 0) / mid.length, mid.reduce((s, m) => s + m[1], 0) / mid.length];
  // the closure is a cluster plus a few outliers: size the zone to the cluster, outliers keep their red lines
  const dist = mid.map((m) => Math.hypot(m[0] - centre[0], m[1] - centre[1])).sort((a, b) => a - b);
  const radius = dist[Math.floor(dist.length * 0.8)] + 0.8;
  const custs = raw.customers.map(([lo, la, d, v]) => ({ p: P([lo, la]), demand: d, vehicle: v }));
  // widest road class with the lowest peak ratio and the most length: take the longest class-3 edge
  let best = 0, bestLen = 0;
  raw.edges.forEach(([a, b, cls], i) => {
    if (cls !== 3) return;
    const l = Math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1]);
    if (l > bestLen) { bestLen = l; best = i; }
  });
  const [ba, bb] = raw.edges[best];
  const bx = nodes.map((n) => n[0]), bz = nodes.map((n) => n[1]);
  const bounds = { minX: Math.min(...bx), maxX: Math.max(...bx), minZ: Math.min(...bz), maxZ: Math.max(...bz) };
  return {
    source: raw.source,
    bounds,
    blocks: makeBlocks(nodes, raw.edges, bounds, P(raw.depot)),
    nodes,
    edges: raw.edges,
    ratioPeak: raw.ratios.peak,
    hourly: raw.hourly,
    depot: P(raw.depot),
    customers: custs,
    capacity: raw.capacity,
    routes: raw.plan.geometry.map((g) => g.map(P)),
    plan: raw.plan,
    incident: {
      segments: segs, centre, radius,
      vehicles: raw.incident.vehicles.map((v) => ({ v: v.v, p: P([v.lon, v.lat]), status: v.status })),
      moved: raw.incident.moved.map((m) => ({ ...m, p: custs[m.customer - 1].p })),
      routes: raw.incident.geometry.map((g) => g.map(P)),
      fallbackLatencyS: raw.incident.fallback_latency_s,
      fallback: raw.incident.fallback, final: raw.incident.final,
      tStartH: raw.incident.t_start_h, tEndH: raw.incident.t_end_h,
    },
    busiest: [(nodes[ba][0] + nodes[bb][0]) / 2, (nodes[ba][1] + nodes[bb][1]) / 2],
    stopOnRoute3: custs[raw.plan.routes[3][4] - 1].p,
  };
}

const mulberry = (a: number) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

function segDist(p: V2, a: V2, b: V2): number {
  const dx = b[0] - a[0], dz = b[1] - a[1], l2 = dx * dx + dz * dz || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / l2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dz));
}

const PAPER = ["#f7efe9", "#efe4d6", "#e9dccb", "#f3e9dd", "#fffaf4", "#f0e2cf"];
const PASTEL = ["#ffd9c2", "#d4e3ff", "#ffdcf1", "#d6f2dd"];

/** A paper-model skyline: boxes dropped on the empty ground between roads (deterministic, so it never reshuffles). */
function makeBlocks(nodes: V2[], edges: [number, number, number, number][], b: SceneData["bounds"], depot: V2): Block[] {
  const rnd = mulberry(7), segs = edges.map(([a, c]) => [nodes[a], nodes[c]] as [V2, V2]);
  const out: Block[] = [];
  for (let i = 0; i < 1400 && out.length < 320; i++) {
    const w = 0.45 + rnd() * 0.55, d = 0.45 + rnd() * 0.55;
    const p: V2 = [b.minX + 1 + rnd() * (b.maxX - b.minX - 2), b.minZ + 1 + rnd() * (b.maxZ - b.minZ - 2)];
    if (Math.hypot(p[0] - depot[0], p[1] - depot[1]) < 3.2) continue;
    const clear = Math.max(w, d) / 2 + 0.28;
    if (segs.some(([s, e]) => segDist(p, s, e) < clear)) continue;
    if (out.some((o) => Math.hypot(o.x - p[0], o.z - p[1]) < (o.w + w) / 2 + 0.12)) continue;
    const tall = rnd() < 0.12;
    out.push({ x: p[0], z: p[1], w, d, h: tall ? 1.2 + rnd() * 1.1 : 0.25 + rnd() * 0.6, c: rnd() < 0.1 ? PASTEL[Math.floor(rnd() * 4)] : PAPER[Math.floor(rnd() * PAPER.length)] });
  }
  return out;
}

/** Colour-blind-safe route palette (Okabe–Ito family, lifted for a dark ground). */
export const ROUTE_COLORS = ["#b8f04a", "#f0b429", "#ff6a45", "#f27fc4", "#4fd1b0", "#b79cff", "#e6e3d3", "#d4a373"];
