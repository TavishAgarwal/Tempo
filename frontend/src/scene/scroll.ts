import Lenis from "lenis";

/** Single source of truth for scroll. Everything reads `scroll.p` inside rAF / useFrame; no React state. */
export const scroll = { p: 0 };

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Starts Lenis smoothing (off for reduced motion) and the progress writer. Returns a cleanup. */
export function startScroll(): () => void {
  const read = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    scroll.p = max > 0 ? clamp01(scrollY / max) : 0;
  };
  read();
  if (reducedMotion()) {
    addEventListener("scroll", read, { passive: true });
    return () => removeEventListener("scroll", read);
  }
  const lenis = new Lenis({ lerp: 0.085, smoothWheel: true });
  let raf = requestAnimationFrame(function loop(t) {
    lenis.raf(t);
    read();
    raf = requestAnimationFrame(loop);
  });
  return () => {
    cancelAnimationFrame(raf);
    lenis.destroy();
  };
}

