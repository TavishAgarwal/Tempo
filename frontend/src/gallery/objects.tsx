import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, type ReactNode } from "react";
import * as THREE from "three";
import { ROUTE_COLORS, type SceneData, type V2 } from "../scene/data";
import { clamp01, roadGeometry, routeMaterial, sampler, stripGeometry } from "../scene/geo";
import { G, actOf, smooth } from "./state";

/**
 * Places an exhibit in its room. `x` and `y` are offsets from the room centre as fractions of the viewport
 * (y up), so every room can compose differently. It grows in on arrival and turns toward the viewer as the page scrolls.
 */
export function Slot({ i, x = 0, y = 0, tilt = 0, children }: { i: number; x?: number; y?: number; tilt?: number; children: ReactNode }) {
  const outer = useRef<THREE.Group>(null), inner = useRef<THREE.Group>(null);
  useFrame(() => {
    const o = outer.current, n = inner.current;
    if (!o || !n) return;
    const a = actOf(i);
    o.visible = a > 0.002;
    const px = G.mobile ? 0 : x, py = G.mobile ? 0.2 : y;
    o.position.set(px * G.S, -i * G.H + py * G.H - 3.3 * G.unit, 0);
    o.scale.setScalar(Math.max(0.001, G.unit * (0.5 + 0.5 * smooth(0, 0.75, a))));
    n.rotation.set(tilt + (G.pos - i) * 0.25, (G.pos - i) * -1.15 + Math.sin(G.t * 0.35 + i) * 0.07, Math.max(-0.22, Math.min(0.22, G.vel * 0.1)), "YXZ");
  });
  return (
    <group ref={outer}>
      <mesh position={[0, 3.3, -6.5]} receiveShadow><planeGeometry args={[40, 30]} /><shadowMaterial transparent opacity={0.11} /></mesh>
      <group ref={inner}>{children}</group>
    </group>
  );
}

const std = (color: string, roughness = 0.8) => <meshStandardMaterial color={color} roughness={roughness} />;

// ------------------------------------------------------------------ 0 / 10: the metronome (its beat is the road speed)

export function Metronome({ i, scale = 1 }: { i: number; scale?: number }) {
  const pend = useRef<THREE.Group>(null), phase = useRef(0);
  const wood = "#d8d4c2", dark = "#2a2c24", tilt = -Math.atan(1.3 / 9);
  useFrame((_, dt) => {
    // one beat per swing: fast at free flow (night), dragging at the evening peak, straight from the hourly profile
    phase.current += dt * 5.5 * Math.pow(G.ratio, 1.4);
    if (pend.current) pend.current.rotation.z = Math.sin(phase.current) * 0.42 * (0.4 + 0.6 * actOf(i));
  });
  return (
    <group scale={scale}>
      <mesh position={[0, 0.3, 0]} castShadow receiveShadow><boxGeometry args={[5.2, 0.6, 3.8]} />{std(dark, 0.85)}</mesh>
      <mesh position={[0, 5.1, 0]} rotation={[0, Math.PI / 4, 0]} castShadow receiveShadow><cylinderGeometry args={[1.13, 2.97, 9, 4]} />{std(wood)}</mesh>
      <mesh position={[0, 5.0, 1.46]} rotation={[tilt, 0, 0]}><boxGeometry args={[0.62, 7.6, 0.05]} />{std("#0c0d0a", 0.9)}</mesh>
      {Array.from({ length: 9 }).map((_, k) => (
        <mesh key={k} position={[0.22, 1.5 + k * 0.82, 1.5 - k * 0.012]} rotation={[tilt, 0, 0]}><boxGeometry args={[0.2, 0.05, 0.02]} /><meshStandardMaterial color="#b8f04a" /></mesh>
      ))}
      <mesh position={[0, 9.7, 0]} castShadow><boxGeometry args={[2.0, 0.35, 1.7]} />{std(dark, 0.85)}</mesh>
      <mesh position={[-1.7, 5.6, -0.1]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.16, 0.16, 0.9, 12]} /><meshStandardMaterial color="#c9a24a" roughness={0.5} metalness={0.2} /></mesh>
      <group ref={pend} position={[0, 1.0, 1.72]}>
        <mesh position={[0, 3.3, 0]} castShadow><boxGeometry args={[0.12, 6.9, 0.1]} /><meshStandardMaterial color="#3a3d32" roughness={0.45} metalness={0.3} /></mesh>
        <mesh position={[0, 4.4, 0]} castShadow><boxGeometry args={[0.75, 0.6, 0.45]} />{std("#b8f04a", 0.6)}</mesh>
        <mesh position={[0, -0.45, 0]} castShadow><sphereGeometry args={[0.3, 16, 16]} /><meshStandardMaterial color="#c9a24a" roughness={0.45} metalness={0.3} /></mesh>
      </group>
    </group>
  );
}

// ------------------------------------------------------------------ 1: the 24-hour dial (real speed profile)

const dialColor = (r: number) => (r < 0.5 ? "#ff6a45" : r < 0.6 ? "#ff9f43" : r < 0.8 ? "#f0b429" : "#b8f04a");

export function Dial({ i, hourly }: { i: number; hourly: Record<string, number[]> }) {
  const outer = useRef<(THREE.Mesh | null)[]>([]), inner = useRef<(THREE.Mesh | null)[]>([]), hand = useRef<THREE.Group>(null);
  const A = hourly["3"], B = hourly["5"];
  const outG = useMemo(() => new THREE.BoxGeometry(1, 0.34, 0.5).translate(0.5, 0, 0), []);
  const inG = useMemo(() => new THREE.BoxGeometry(1, 0.26, 0.5).translate(-0.5, 0, 0), []);
  useFrame(() => {
    const k = smooth(0.05, 0.85, actOf(i));
    for (let h = 0; h < 24; h++) {
      const o = outer.current[h], n = inner.current[h];
      if (o) o.scale.x = Math.max(0.001, k * 3.4 * A[h]);
      if (n) n.scale.x = Math.max(0.001, k * 1.5 * B[h]);
    }
    if (hand.current) hand.current.rotation.z = Math.PI / 2 - (17.5 / 24) * Math.PI * 2 * smooth(0.1, 0.9, actOf(i));
  });
  return (
    <group position={[0, 3.4, 0]} rotation={[-0.12, 0, 0]} scale={0.88}>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -0.3]} castShadow receiveShadow><cylinderGeometry args={[6.3, 6.3, 0.5, 72]} />{std("#14150f", 0.9)}</mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -0.02]}><torusGeometry args={[2.15, 0.05, 8, 72]} />{std("#e6e3d3")}</mesh>
      {Array.from({ length: 24 }).map((_, h) => {
        const a = Math.PI / 2 - ((h + 0.5) / 24) * Math.PI * 2;
        return (
          <group key={h} rotation={[0, 0, a]}>
            <mesh ref={(m) => { outer.current[h] = m; }} geometry={outG} position={[2.3, 0, 0]} castShadow><meshStandardMaterial color={dialColor(A[h])} roughness={0.7} /></mesh>
            <mesh ref={(m) => { inner.current[h] = m; }} geometry={inG} position={[2.0, 0, 0]}><meshStandardMaterial color={dialColor(B[h])} roughness={0.7} /></mesh>
          </group>
        );
      })}
      {[0, 6, 12, 18].map((h) => {
        const a = Math.PI / 2 - (h / 24) * Math.PI * 2;
        return <mesh key={h} position={[Math.cos(a) * 5.95, Math.sin(a) * 5.95, 0.05]} castShadow><boxGeometry args={[0.28, 0.28, 0.4]} />{std("#e6e3d3")}</mesh>;
      })}
      <group ref={hand}>
        <mesh position={[1.1, 0, 0.35]} castShadow><boxGeometry args={[2.2, 0.1, 0.12]} />{std("#e6e3d3", 0.5)}</mesh>
        <mesh position={[0, 0, 0.35]}><cylinderGeometry args={[0.22, 0.22, 0.2, 20]} />{std("#e6e3d3")}</mesh>
      </group>
    </group>
  );
}

// ------------------------------------------------------------------ 2: the 100 parcels

export function ParcelCity({ i, data }: { i: number; data: SceneData }) {
  const g = useRef<THREE.Group>(null);
  const order = useMemo(() => [...data.customers].sort((a, b) => a.vehicle - b.vehicle || b.demand - a.demand), [data]);
  const boxG = useMemo(() => new THREE.BoxGeometry(0.5, 1, 0.5).translate(0, 0.5, 0), []);
  const tapeG = useMemo(() => new THREE.BoxGeometry(0.13, 1, 0.52).translate(0, 0.5, 0), []);
  const init = (tape: boolean) => (m: THREE.InstancedMesh | null) => {
    if (!m) return;
    const o = new THREE.Object3D(), col = new THREE.Color();
    order.forEach((c, k) => {
      const gx = k % 10, gz = Math.floor(k / 10), h = 0.35 + c.demand * 0.3;
      o.position.set((gx - 4.5) * 0.62, 0.0, (gz - 4.5) * 0.62);
      o.scale.set(1, tape ? h * 1.004 + 0.004 : h, 1);
      o.rotation.set(0, ((k * 37) % 7) * 0.05 - 0.15, 0); o.updateMatrix();
      m.setMatrixAt(k, o.matrix); m.setColorAt(k, col.set(tape ? ROUTE_COLORS[c.vehicle] : "#cfa066"));
    });
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  };
  useFrame(() => { if (g.current) g.current.scale.y = Math.max(0.001, smooth(0.05, 0.8, actOf(i))); });
  return (
    <group>
      <mesh position={[0, 0.2, 0]} receiveShadow castShadow><boxGeometry args={[7.2, 0.4, 7.2]} />{std("#0c0d0a", 0.9)}</mesh>
      <group ref={g} position={[0, 0.4, 0]}>
        <instancedMesh ref={init(false)} args={[boxG, undefined, order.length]} castShadow receiveShadow>{std("#cfa066", 0.95)}</instancedMesh>
        <instancedMesh ref={init(true)} args={[tapeG, undefined, order.length]} castShadow>{std("#ffffff", 0.6)}</instancedMesh>
      </group>
    </group>
  );
}

// ------------------------------------------------------------------ 3 / 4 / 5: the Delhi model on a plinth

function Van({ mat, vref }: { mat: THREE.Material; vref: (g: THREE.Group | null) => void }) {
  return (
    <group ref={vref} visible={false} scale={3.4}>
      <mesh position={[0, 0.2, 0]} castShadow material={mat}><boxGeometry args={[0.62, 0.3, 0.32]} /></mesh>
      <mesh position={[0.24, 0.17, 0]} material={mat}><boxGeometry args={[0.2, 0.24, 0.3]} /></mesh>
      {[[-0.2, 0.17], [0.22, 0.17], [-0.2, -0.17], [0.22, -0.17]].map(([x, z], k) => (
        <mesh key={k} position={[x, 0.07, z]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.07, 0.07, 0.06, 12]} />{std("#171717", 0.9)}</mesh>
      ))}
    </group>
  );
}

export type DioramaMode = "route" | "closure" | "recovery";
const GREY = "#7d7b6c";
const CYCLE = 5.5; // seconds per replayed van

/**
 * The Delhi demo on a plinth. To stay readable it never draws all eight routes at full strength:
 *  route    - replays one van at a time (draw-in, then a van drives it), the others stay faint
 *  closure  - routes faint, the closed segments, hatched zone and cones loud
 *  recovery - only the van that takes over the most parcels: its old route (grey) against its new one
 */
export function Diorama({ i, mode, data }: { i: number; mode: DioramaMode; data: SceneData }) {
  const B = data.bounds, I = data.incident;
  const k = Math.min(9.4 / (B.maxX - B.minX), 7.0 / (B.maxZ - B.minZ));
  const cx = (B.maxX + B.minX) / 2, cz = (B.maxZ + B.minZ) / 2;
  const fvRec = useMemo(() => {
    const c: Record<number, number> = {};
    I.moved.forEach((m) => { c[m.to] = (c[m.to] ?? 0) + 1; });
    return Number(Object.entries(c).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 0);
  }, [I]);
  const gained = useMemo(() => I.moved.filter((m) => m.to === fvRec).length, [I, fvRec]);
  const stops = useMemo(() => ROUTE_COLORS.map((_, v) => data.customers.filter((c) => c.vehicle === v)), [data]);

  const roads = useMemo(() => roadGeometry(data.nodes, data.edges, 3.2), [data]);
  const baseMats = useMemo(() => ROUTE_COLORS.map((c) => routeMaterial(mode === "route" ? c : GREY)), [mode]);
  const afterMats = useMemo(() => ROUTE_COLORS.map(routeMaterial), []);
  const baseGeo = useMemo(() => data.routes.map((r) => stripGeometry(r, 0.5, 0.5)), [data]);
  const afterGeo = useMemo(() => I.routes.map((r) => stripGeometry(r, 0.56, 0.7)), [I]);
  const baseS = useMemo(() => data.routes.map(sampler), [data]);
  const afterS = useMemo(() => I.routes.map(sampler), [I]);
  const incMat = useMemo(() => routeMaterial("#ff6a45"), []);
  const incGeo = useMemo(() => roadGeometry(I.segments.flat(), I.segments.map((_s, n): [number, number, number, number] => [n * 2, n * 2 + 1, 3, 0]), 3.2), [I]);
  const vanMat = useMemo(() => new THREE.MeshStandardMaterial({ color: ROUTE_COLORS[1], roughness: 0.8 }), []);
  const blockG = useMemo(() => new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0), []);
  const coneG = useMemo(() => new THREE.ConeGeometry(0.5, 1.5, 12).translate(0, 0.75, 0), []);
  const dotG = useMemo(() => new THREE.SphereGeometry(0.34, 10, 10), []);
  const zoneMat = useMemo(() => new THREE.MeshBasicMaterial({ color: "#f0b429", transparent: true, opacity: 0.22, depthWrite: false }), []);
  const dotMat = useMemo(() => new THREE.MeshBasicMaterial({ color: "#ffffff" }), []);
  const van = useRef<THREE.Group>(null), cones = useRef<THREE.Group>(null), rings = useRef<THREE.Group>(null), dots = useRef<THREE.InstancedMesh>(null);
  const last = useRef(-1);
  const blocks = useMemo(() => data.blocks.filter((_b, n) => n % 2 === 0), [data]);
  const conePts = useMemo(() => I.segments.map(([a, b], n) => {
    const mx = (a[0] + b[0]) / 2, mz = (a[1] + b[1]) / 2, dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz) || 1, off = (n % 2 ? 1 : -1) * 0.3;
    return [mx - (dz / l) * off, mz + (dx / l) * off] as V2;
  }), [I]);
  const blocksInit = (m: THREE.InstancedMesh | null) => {
    if (!m) return;
    const o = new THREE.Object3D(), col = new THREE.Color();
    blocks.forEach((b, n) => { o.position.set(b.x, 0, b.z); o.scale.set(b.w * 0.85, b.h * 0.8, b.d * 0.85); o.updateMatrix(); m.setMatrixAt(n, o.matrix); m.setColorAt(n, col.setHSL(0.17, 0.08, 0.16 + (n % 5) * 0.025)); });
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  };
  const conesInit = (m: THREE.InstancedMesh | null) => {
    if (!m) return;
    const o = new THREE.Object3D();
    conePts.forEach((p, n) => { o.position.set(p[0], 0, p[1]); o.updateMatrix(); m.setMatrixAt(n, o.matrix); });
    m.instanceMatrix.needsUpdate = true;
  };

  useFrame(() => {
    const a = actOf(i), enter = smooth(0.05, 0.85, a);
    const fv = mode === "route" ? Math.floor(G.t / CYCLE) % ROUTE_COLORS.length : fvRec;
    const draw = clamp01(((G.t % CYCLE) / CYCLE) / 0.7) * enter;
    const faint = mode === "route" ? 0.15 : mode === "closure" ? 0.2 : 0.1;

    baseMats.forEach((m, v) => {
      const focus = mode !== "closure" && v === fv;
      m.uniforms.uProg.value = focus && mode === "route" ? draw : 1;
      m.uniforms.uOpacity.value = (focus ? (mode === "route" ? 1 : 0.5) : faint) * enter;
    });
    afterMats.forEach((m, v) => {
      const on = mode === "recovery" && v === fvRec;
      m.uniforms.uProg.value = on ? clamp01(smooth(0.1, 0.9, a) * 1.1) : 0;
      m.uniforms.uOpacity.value = 1;
    });
    incMat.uniforms.uProg.value = 1;
    incMat.uniforms.uOpacity.value = mode === "route" ? 0 : (mode === "closure" ? 1 : 0.3) * smooth(0.15, 0.7, a);
    zoneMat.opacity = mode === "route" ? 0 : (mode === "closure" ? 0.3 : 0.1) * smooth(0.15, 0.7, a);
    if (cones.current) cones.current.scale.y = Math.max(0.001, mode === "route" ? 0 : smooth(0.2, 0.8, a) * (mode === "recovery" ? 0.5 : 1));
    if (rings.current) rings.current.children.forEach((c, n) => c.scale.setScalar(Math.max(0.001, (mode === "recovery" ? smooth(0.4, 0.9, a) : 0) * (1 + 0.15 * Math.sin(G.t * 3 + n)))));

    // the van replays the focus route
    if (van.current) {
      const s = mode === "route" ? baseS[fv](draw) : mode === "recovery" ? afterS[fvRec]((G.t * 0.14) % 1) : null;
      van.current.visible = !!s && enter > 0.9 && (mode !== "route" || draw > 0.02);
      if (s) { van.current.position.set(s[0], 0.5, s[1]); van.current.rotation.y = -s[2]; }
      vanMat.color.set(ROUTE_COLORS[fv]);
    }
    // numbered stops of the focus van
    const key = mode === "closure" ? -2 : fv;
    if (dots.current && key !== last.current) {
      last.current = key;
      const o = new THREE.Object3D(), list = key >= 0 ? stops[key] : [];
      dots.current.count = list.length;
      list.forEach((c, n) => { o.position.set(c.p[0], 0.9, c.p[1]); o.updateMatrix(); dots.current!.setMatrixAt(n, o.matrix); });
      dots.current.instanceMatrix.needsUpdate = true;
      dotMat.color.set(key >= 0 ? ROUTE_COLORS[key] : "#ffffff");
    }
    if (a > 0.6) G.chip[i] = mode === "route" ? `replaying van ${fv + 1} · ${stops[fv].length} parcels` : mode === "recovery" ? `van ${fvRec + 1} takes over ${gained} parcels` : "";
  });

  return (
    <group>
      <mesh position={[0, 0.25, 0]} receiveShadow castShadow><boxGeometry args={[10.2, 0.5, 7.9]} />{std("#15160f", 0.9)}</mesh>
      <mesh position={[0, 0.05, 0]}><boxGeometry args={[10.45, 0.12, 8.15]} />{std("#b8f04a", 0.9)}</mesh>
      <group position={[0, 0.5, 0]}>
        <group scale={k} position={[-cx * k, 0, -cz * k]}>
          <mesh geometry={roads} position={[0, 0.05, 0]}><meshBasicMaterial color="#e6e3d3" transparent opacity={mode === "closure" ? 0.34 : 0.2} depthWrite={false} /></mesh>
          <instancedMesh ref={blocksInit} args={[blockG, undefined, blocks.length]} castShadow receiveShadow>{std("#ffffff", 1)}</instancedMesh>
          {baseGeo.map((g, n) => <mesh key={`b${n}`} geometry={g} material={baseMats[n]} frustumCulled={false} renderOrder={2} />)}
          {afterGeo.map((g, n) => <mesh key={`a${n}`} geometry={g} material={afterMats[n]} frustumCulled={false} renderOrder={3} />)}
          <mesh geometry={incGeo} material={incMat} position={[0, 0.6, 0]} frustumCulled={false} renderOrder={4} />
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[I.centre[0], 0.12, I.centre[1]]} material={zoneMat}><circleGeometry args={[I.radius, 48]} /></mesh>
          <group ref={cones}><instancedMesh ref={conesInit} args={[coneG, undefined, conePts.length]} castShadow>{std("#ff6a45", 0.7)}</instancedMesh></group>
          <instancedMesh ref={dots} args={[dotG, dotMat, 40]} count={0} />
          <group ref={rings}>
            {I.moved.filter((m) => m.to === fvRec).map((m) => <mesh key={m.customer} position={[m.p[0], 1.1, m.p[1]]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[0.75, 1.05, 24]} /><meshBasicMaterial color={ROUTE_COLORS[m.to]} side={THREE.DoubleSide} /></mesh>)}
          </group>
          <group position={[data.depot[0], 0.1, data.depot[1]]} scale={1.5}>
            <mesh position={[0, 0.5, 0]} castShadow><boxGeometry args={[2.1, 1, 1.55]} />{std("#e6e3d3", 0.9)}</mesh>
            <mesh position={[0, 1.2, 0]}><boxGeometry args={[2.3, 0.4, 1.7]} />{std("#b8f04a", 0.8)}</mesh>
          </group>
          <Van mat={vanMat} vref={(g) => { (van as { current: THREE.Group | null }).current = g; }} />
        </group>
      </group>
    </group>
  );
}

// ------------------------------------------------------------------ 6: the seven solver steps as stations on a conveyor

export function Pipeline({ i }: { i: number }) {
  const hexes = useRef<(THREE.Mesh | null)[]>([]), token = useRef<THREE.Mesh>(null);
  const pts = useMemo(() => Array.from({ length: 7 }, (_, n): [number, number] => [(n - 3) * 2.3, Math.sin(n * 0.9) * 1.5]), []);
  useFrame(() => {
    const a = actOf(i);
    hexes.current.forEach((m, n) => { if (m) m.scale.y = Math.max(0.001, smooth(n * 0.06, 0.5 + n * 0.06, a)); });
    if (token.current) {
      const s = ((G.t * 0.22) % 1) * 6, n = Math.min(5, Math.floor(s)), u = s - n;
      token.current.position.set(pts[n][0] + (pts[n + 1][0] - pts[n][0]) * u, 1.25 + Math.sin(u * Math.PI) * 0.5, pts[n][1] + (pts[n + 1][1] - pts[n][1]) * u);
      token.current.visible = a > 0.5;
    }
  });
  return (
    <group>
      {pts.slice(0, 6).map(([x, z], n) => {
        const [x2, z2] = pts[n + 1], dx = x2 - x, dz = z2 - z, len = Math.hypot(dx, dz);
        return <mesh key={`c${n}`} position={[(x + x2) / 2, 0.12, (z + z2) / 2]} rotation={[0, -Math.atan2(dz, dx), 0]} receiveShadow><boxGeometry args={[len, 0.24, 0.5]} />{std("#0c0d0a", 0.9)}</mesh>;
      })}
      {pts.map(([x, z], n) => {
        const vnd = n === 3, ghost = n === 6, h = vnd ? 2.4 : 0.9;
        return (
          <mesh key={n} ref={(m) => { hexes.current[n] = m; }} position={[x, h / 2 + 0.2, z]} scale-y={0.001} castShadow receiveShadow>
            <cylinderGeometry args={[1.0, 1.0, h, 6]} />
            {ghost ? <meshBasicMaterial color="#e6e3d3" wireframe /> : std(vnd ? "#0c0d0a" : "#e6e3d3", 0.8)}
          </mesh>
        );
      })}
      <mesh ref={token} castShadow><sphereGeometry args={[0.36, 16, 16]} /><meshStandardMaterial color="#b8f04a" roughness={0.5} /></mesh>
    </group>
  );
}

// ------------------------------------------------------------------ 8: static vs time-dependent, nearly the same length

export function BarPair({ i }: { i: number }) {
  const a = useRef<THREE.Mesh>(null), b = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const k = smooth(0.05, 0.8, actOf(i));
    if (a.current) { a.current.scale.x = Math.max(0.001, k * 6.4); a.current.position.x = -3.2 + (k * 6.4) / 2; }
    if (b.current) { b.current.scale.x = Math.max(0.001, k * 6.4 * 0.995); b.current.position.x = -3.2 + (k * 6.4 * 0.995) / 2; }
  });
  return (
    <group>
      <mesh position={[0, 0.2, 0]} receiveShadow castShadow><boxGeometry args={[8, 0.4, 5]} />{std("#0c0d0a", 0.9)}</mesh>
      <mesh ref={a} position={[0, 0.95, 1.1]} castShadow><boxGeometry args={[1, 1.1, 1.5]} />{std("#8f8d7c", 0.8)}</mesh>
      <mesh ref={b} position={[0, 0.95, -1.1]} castShadow><boxGeometry args={[1, 1.1, 1.5]} />{std("#b8f04a", 0.7)}</mesh>
    </group>
  );
}

// ------------------------------------------------------------------ 9: what is not built yet, drawn as wireframe

/** A second depot, a different truck and a stack of parcels: the single-depot, single-vehicle-type limits, still only outlines. */
export function Ghost({ i }: { i: number }) {
  const g = useRef<THREE.Group>(null);
  useFrame(() => { if (g.current) g.current.rotation.y = Math.sin(G.t * 0.3) * 0.35 * (0.4 + actOf(i)); });
  const wire = <meshBasicMaterial color="#e6e3d3" wireframe />;
  const roof = useMemo(() => { const s = new THREE.Shape(); s.moveTo(-1.15, 0); s.lineTo(1.15, 0); s.lineTo(0, 0.75); s.closePath(); return new THREE.ExtrudeGeometry(s, { depth: 1.7, bevelEnabled: false }).translate(0, 0, -0.85); }, []);
  return (
    <group ref={g}>
      <mesh position={[0, -0.15, 0]}><boxGeometry args={[7.5, 0.3, 4.4]} />{wire}</mesh>
      <group position={[-2.3, 0, -0.6]} scale={1.2}>
        <mesh position={[0, 0.5, 0]}><boxGeometry args={[2.1, 1, 1.55]} />{wire}</mesh>
        <mesh geometry={roof} position={[0, 1, 0]}>{wire}</mesh>
      </group>
      <group position={[2.2, 0, 0.5]}>
        <mesh position={[0, 0.95, 0]}><boxGeometry args={[3.2, 1.5, 1.4]} />{wire}</mesh>
        <mesh position={[1.9, 0.75, 0]}><boxGeometry args={[0.9, 1.1, 1.3]} />{wire}</mesh>
        {[-1, 0.7, 1.9].map((x) => [0.75, -0.75].map((z) => <mesh key={`${x}${z}`} position={[x, 0.2, z]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.32, 0.32, 0.25, 10]} />{wire}</mesh>))}
      </group>
      {[[0, 0, 1.4], [0.9, 0, 1.4], [0.45, 0.85, 1.4]].map(([x, y, z], n) => <mesh key={n} position={[x - 0.3, y + 0.4, z]}><boxGeometry args={[0.8, 0.8, 0.8]} />{wire}</mesh>)}
    </group>
  );
}
