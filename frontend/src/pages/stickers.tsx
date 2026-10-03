/** Flat peel-and-stick stickers: 2px charcoal outline, vivid fills, placed at a slight rotation. Decorative only. */
const S = { stroke: "#171717", strokeWidth: 2.4, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };

export type StickerKind = "bolt" | "cone" | "parcel" | "clock" | "heart" | "pin" | "sparkle" | "van";

export function Sticker({ kind, className = "" }: { kind: StickerKind; className?: string }) {
  return (
    <svg className={`stk ${className}`} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      {kind === "bolt" && <path d="M36 5 14 36h14l-5 23 27-33H35z" fill="#3b82f6" {...S} />}
      {kind === "cone" && <>
        <path d="M32 6 46 50H18z" fill="#ff6f1e" {...S} />
        <path d="M26.5 24h11l2.6 9H23.9z" fill="#fdfbf9" {...S} strokeWidth={2} />
        <rect x="10" y="50" width="44" height="8" rx="3" fill="#2b1a07" {...S} />
      </>}
      {kind === "parcel" && <>
        <path d="M8 22 32 12l24 10v26L32 58 8 48z" fill="#cfa066" {...S} />
        <path d="M8 22 32 32l24-10M32 32v26" fill="none" {...S} />
        <path d="M20 17l24 10v9l-6-2.5v-6.5L14 17z" fill="#3b82f6" {...S} strokeWidth={2} />
      </>}
      {kind === "clock" && <>
        <circle cx="32" cy="34" r="21" fill="#ff66cf" {...S} />
        <circle cx="32" cy="34" r="15" fill="#fdfbf9" {...S} strokeWidth={2} />
        <path d="M32 34V24M32 34l7 4" fill="none" {...S} />
        <path d="M14 14l7 6M50 14l-7 6" fill="none" {...S} />
      </>}
      {kind === "heart" && <>
        <path d="M32 56C10 40 6 28 10 19c4-9 16-9 22 1 6-10 18-10 22-1 4 9 0 21-22 37z" fill="#ff66cf" {...S} />
        <circle cx="24" cy="28" r="3.4" fill="#171717" /><circle cx="40" cy="28" r="3.4" fill="#171717" />
        <path d="M27 37q5 4 10 0" fill="none" {...S} strokeWidth={2} />
      </>}
      {kind === "pin" && <>
        <path d="M32 58C18 42 12 34 12 24a20 20 0 0 1 40 0c0 10-6 18-20 34z" fill="#22c55e" {...S} />
        <circle cx="32" cy="24" r="8" fill="#fdfbf9" {...S} />
      </>}
      {kind === "sparkle" && <path d="M32 4c2 14 6 20 28 28-22 8-26 14-28 28-2-14-6-20-28-28 22-8 26-14 28-28z" fill="#ffd23f" {...S} />}
      {kind === "van" && <>
        <path d="M5 20h36v22H5z" fill="#ff6f1e" {...S} />
        <path d="M41 28h10l8 8v6H41z" fill="#ff6f1e" {...S} />
        <path d="M45 31h5l4 5h-9z" fill="#fdfbf9" {...S} strokeWidth={2} />
        <circle cx="18" cy="45" r="7" fill="#171717" {...S} /><circle cx="48" cy="45" r="7" fill="#171717" {...S} />
      </>}
    </svg>
  );
}

/** A wobbly hand-drawn arrow; `flip` mirrors it. */
export function Arrow({ className = "", flip = false }: { className?: string; flip?: boolean }) {
  return (
    <svg className={`arrow ${className}`} viewBox="0 0 120 80" aria-hidden="true" focusable="false" style={flip ? { transform: "scaleX(-1)" } : undefined}>
      <path d="M6 10C34 2 72 6 94 34c6 8 10 18 11 30" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M92 52l13 15 10-16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Small metronome mark for the top-left of the page. */
export function Mark() {
  return (
    <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
      <path d="M12 4h8l6 24H6z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M16 24 21 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="19" cy="14" r="2.2" fill="#b8f04a" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
