import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { SceneData } from "../scene/data";
import { reducedMotion, scroll } from "../scene/scroll";
import { BarPair, Dial, Diorama, Ghost, Metronome, ParcelCity, Pipeline, Slot } from "./objects";
import { G, ROOMS } from "./state";

const CAM_Z = 22, FOV = 30;

/** Writes the shared gallery state once per frame and slides the camera along the corridor of exhibits. */
function Rig({ hourly }: { hourly: number[] }) {
  const { camera, size } = useThree();
  const last = useRef(0);
  const reduced = useMemo(reducedMotion, []);
  const light = useRef<THREE.DirectionalLight>(null);
  const target = useMemo(() => new THREE.Object3D(), []);

  useFrame(({ clock }, dt) => {
    G.t = clock.elapsedTime;
    G.pos = scroll.p * (ROOMS - 1);
    const v = dt > 0 ? (G.pos - last.current) / dt : 0;
    G.vel += ((reduced ? 0 : v) - G.vel) * Math.min(1, dt * 6);
    last.current = G.pos;

    const aspect = size.width / size.height;
    const visH = 2 * CAM_Z * Math.tan((FOV * Math.PI) / 360);
    G.H = visH;
    G.S = visH * aspect;
    G.mobile = aspect < 0.85;
    G.unit = Math.min(0.85, Math.max(0.24, (G.S / 15) * 0.62));
    // a looping 'day': the metronome beats at the real main-road speed of that hour
    G.hour = (G.t * 1.2) % 24;
    const h0 = Math.floor(G.hour), f = G.hour - h0;
    G.ratio = hourly[h0] * (1 - f) + hourly[(h0 + 1) % 24] * f;

    // a level camera drops down the column of exhibits, one viewport height per room
    const y = -G.pos * G.H;
    camera.position.set(0, y, CAM_Z);
    const l = light.current;
    if (l) { l.position.set(-8, y + 12, 16); target.position.set(0, y, -2); target.updateMatrixWorld(); }
  });
  return (
    <>
      <hemisphereLight args={["#fff6ea", "#d9cdbd", 1.25]} />
      <primitive object={target} />
      <directionalLight ref={light} target={target} intensity={1.5} castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-13} shadow-camera-right={13} shadow-camera-top={13} shadow-camera-bottom={-13} shadow-camera-near={1} shadow-camera-far={60} shadow-bias={-0.0004} />
    </>
  );
}

/** One transparent canvas above the coloured rooms: each room has one exhibit built from the project's real data. */
export default function Stage({ data }: { data: SceneData }) {
  return (
    <div className="g-stage" aria-hidden="true">
      <Canvas shadows dpr={[1, 2]} camera={{ fov: FOV, near: 0.1, far: 200, position: [0, 0, CAM_Z] }} gl={{ antialias: true, alpha: true, toneMapping: THREE.NoToneMapping }}>
        <Rig hourly={data.hourly["3"]} />
        <Slot i={0} x={0.24} y={-0.05}><Metronome i={0} scale={0.92} /></Slot>
        <Slot i={1} x={0.17} y={-0.1}><Dial i={1} hourly={data.hourly} /></Slot>
        <Slot i={2} x={0.2} y={0.1} tilt={0.3}><ParcelCity i={2} data={data} /></Slot>
        <Slot i={3} x={-0.12} y={-0.02} tilt={0.55}><Diorama i={3} mode="route" data={data} /></Slot>
        <Slot i={4} x={-0.14} y={-0.05} tilt={0.55}><Diorama i={4} mode="closure" data={data} /></Slot>
        <Slot i={5} x={-0.17} y={-0.02} tilt={0.55}><Diorama i={5} mode="recovery" data={data} /></Slot>
        <Slot i={6} x={0} y={-0.1} tilt={0.55}><Pipeline i={6} /></Slot>
        <Slot i={8} x={0.22} y={-0.18} tilt={0.3}><BarPair i={8} /></Slot>
        <Slot i={9} x={0.22} y={0.12} tilt={0.2}><Ghost i={9} /></Slot>
        <Slot i={10} x={0.25} y={-0.05}><Metronome i={10} scale={0.8} /></Slot>
      </Canvas>
    </div>
  );
}
