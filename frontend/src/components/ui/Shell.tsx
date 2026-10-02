import { useEffect, useState, type ReactNode } from "react";

function useMedia(q: string): boolean {
  const [m, setM] = useState(() => matchMedia(q).matches);
  useEffect(() => {
    const mq = matchMedia(q);
    const h = () => setM(mq.matches);
    mq.addEventListener("change", h);
    return () => mq.removeEventListener("change", h);
  }, [q]);
  return m;
}

/**
 * Page layout per design.md §2.
 * Desktop (>=1024): left panel | map | right panel.
 * Tablet (768-1023): left panel | map, right panel becomes a bottom sheet.
 * Mobile (<768): full-screen map, tabbed bottom sheet (Plan | Controls), controls are view-only.
 */
export default function Shell({ left, right, rightTitle, children }: { left: ReactNode; right: ReactNode; rightTitle: string; children: ReactNode }) {
  const desktop = useMedia("(min-width: 1024px)");
  const tablet = useMedia("(min-width: 768px)");
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState<"right" | "left">("right");

  if (desktop) {
    return (
      <div className="flex h-full gap-2">
        <aside className="glass tick w-80 shrink-0 space-y-4 overflow-y-auto p-4">{left}</aside>
        <main className="glass tick relative min-h-0 min-w-0 flex-1 overflow-hidden">{children}</main>
        <aside className="glass tick w-96 shrink-0 space-y-4 overflow-y-auto p-4">{right}</aside>
      </div>
    );
  }
  const sheetBtn = "px-3 py-1 text-sm";
  return (
    <div className="relative flex h-full">
      {tablet && <aside className="glass mr-3 w-72 shrink-0 space-y-3 overflow-y-auto  p-3">{left}</aside>}
      <main className="relative min-h-0 min-w-0 flex-1">{children}</main>
      <section aria-label={rightTitle} className="glass absolute inset-x-0 bottom-0 z-[1000] " style={tablet ? { left: "19rem" } : undefined}>
        <div className="flex items-center gap-1 border-b border-border px-2">
          {!tablet && <button className={`${sheetBtn} ${tab === "right" ? "border-b-2 border-primary" : "text-muted"}`} onClick={() => { setTab("right"); setOpen(true); }}>{rightTitle}</button>}
          {!tablet && <button className={`${sheetBtn} ${tab === "left" ? "border-b-2 border-primary" : "text-muted"}`} onClick={() => { setTab("left"); setOpen(true); }}>Controls</button>}
          {tablet && <span className={sheetBtn}>{rightTitle}</span>}
          <button className="ml-auto px-3 py-1 text-sm" aria-expanded={open} aria-label={open ? "Collapse panel" : "Expand panel"} onClick={() => setOpen(!open)}>{open ? "▾" : "▴"}</button>
        </div>
        {open && (
          <div className="max-h-[45vh] space-y-3 overflow-y-auto p-3">
            {tab === "right" || tablet ? right : <>
              <p className="text-xs text-muted">View-only on phones: open the dashboard on a tablet or desktop to change settings or start a solve.</p>
              <div className="pointer-events-none opacity-60" aria-disabled="true">{left}</div>
            </>}
          </div>
        )}
      </section>
    </div>
  );
}
