/** Shared, mutable gallery state: written once per frame by the Rig, read by every exhibit (no React state). */
export const G = {
  pos: 0, // scroll position in rooms: 0 .. N-1
  vel: 0, // smoothed scroll speed, rooms per second
  t: 0, // seconds
  S: 16, // world units per viewport width, at the exhibit plane
  H: 12, // world units per viewport height (one room), at the exhibit plane
  hour: 0, // a looping 'day' (hours 0..24) that drives the metronome from the real speed profile
  ratio: 1, // main-road speed as a share of free flow at that hour
  mobile: false,
  chip: {} as Record<number, string>, // live captions written by exhibits, shown by the page
  unit: 1, // exhibit scale for the current screen
};

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const smooth = (a: number, b: number, x: number) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };

/** 1 when the camera is on room i, falling to 0 one room away. */
export const actOf = (i: number) => clamp01(1 - Math.abs(G.pos - i));

export const ROOMS = 11;
