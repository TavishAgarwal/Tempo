import * as THREE from "three";
import type { V2 } from "./data";

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

// Shader colours are plain sRGB numbers (no colour-space conversion), so THREE.Color uniforms are converted back.
export const srgb = (hex: string) => new THREE.Color(hex).convertLinearToSRGB();

/** Road ribbons from graph edges: one quad per segment, width by road class. */
export function roadGeometry(nodes: V2[], edges: [number, number, number, number][], wScale = 1): THREE.BufferGeometry {
  const widths: Record<number, number> = { 3: 0.22, 4: 0.17, 5: 0.115, 6: 0.085 };
  const n = edges.length;
  const pos = new Float32Array(n * 12), idx = new Uint32Array(n * 6);
  edges.forEach(([a, b, c], i) => {
    const A = nodes[a], B = nodes[b], w = (widths[c] ?? 0.09) * wScale;
    let dx = B[0] - A[0], dz = B[1] - A[1];
    const L = Math.hypot(dx, dz) || 1;
    dx /= L; dz /= L;
    const nx = -dz * w, nz = dx * w, ex = dx * w * 0.5, ez = dz * w * 0.5;
    pos.set([A[0] - ex + nx, 0, A[1] - ez + nz, A[0] - ex - nx, 0, A[1] - ez - nz, B[0] + ex + nx, 0, B[1] + ez + nz, B[0] + ex - nx, 0, B[1] + ez - nz], i * 12);
    idx.set([i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 1, i * 4 + 3, i * 4 + 2], i * 6);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
}

/** A ribbon along a polyline; aT is the fraction of the route length, so a uniform can draw it in. */
export function stripGeometry(raw: V2[], w: number, y: number): THREE.BufferGeometry {
  const pts = raw.filter((p, i) => i === 0 || Math.hypot(p[0] - raw[i - 1][0], p[1] - raw[i - 1][1]) > 1e-4);
  const n = pts.length;
  const g = new THREE.BufferGeometry();
  if (n < 2) return g;
  const pos = new Float32Array(n * 6), side = new Float32Array(n * 2), t = new Float32Array(n * 2);
  const cum = [0];
  for (let i = 1; i < n; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const total = cum[n - 1] || 1;
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
    let dx = b[0] - a[0], dz = b[1] - a[1];
    const L = Math.hypot(dx, dz) || 1;
    dx /= L; dz /= L;
    pos.set([pts[i][0] - dz * w, y, pts[i][1] + dx * w], i * 6);
    pos.set([pts[i][0] + dz * w, y, pts[i][1] - dx * w], i * 6 + 3);
    side[i * 2] = 1; side[i * 2 + 1] = -1;
    t[i * 2] = t[i * 2 + 1] = cum[i] / total;
  }
  const idx: number[] = [];
  for (let i = 0; i < n - 1; i++) idx.push(2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 1, 2 * i + 3, 2 * i + 2);
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("aSide", new THREE.BufferAttribute(side, 1));
  g.setAttribute("aT", new THREE.BufferAttribute(t, 1));
  g.setIndex(idx);
  return g;
}

/** Position + heading at fraction f along a polyline, for the vans. */
export function sampler(raw: V2[]) {
  const pts = raw.filter((p, i) => i === 0 || Math.hypot(p[0] - raw[i - 1][0], p[1] - raw[i - 1][1]) > 1e-4);
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const total = cum[cum.length - 1] || 0;
  return (f: number): [number, number, number] | null => {
    if (pts.length < 2) return pts.length ? [pts[0][0], pts[0][1], 0] : null;
    const target = clamp01(f) * total;
    let i = 1;
    while (i < pts.length - 1 && cum[i] < target) i++;
    const a = pts[i - 1], b = pts[i], seg = cum[i] - cum[i - 1] || 1, u = (target - cum[i - 1]) / seg;
    return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, Math.atan2(b[1] - a[1], b[0] - a[0])];
  };
}

const ROUTE_V = /* glsl */ `
  attribute float aSide; attribute float aT;
  varying float vSide; varying float vT;
  void main() { vSide = aSide; vT = aT; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const ROUTE_F = /* glsl */ `
  uniform vec3 uColor; uniform float uProg; uniform float uOpacity;
  varying float vSide; varying float vT;
  void main() {
    if (vT > uProg) discard;
    gl_FragColor = vec4(uColor, smoothstep(1.0, 0.5, abs(vSide)) * uOpacity);
  }`;

/** Flat marker-colour ribbon that draws itself in as uProg goes 0 to 1. */
export const routeMaterial = (color: string) =>
  new THREE.ShaderMaterial({
    vertexShader: ROUTE_V, fragmentShader: ROUTE_F, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uColor: { value: srgb(color) }, uProg: { value: 0 }, uOpacity: { value: 1 } },
  });
