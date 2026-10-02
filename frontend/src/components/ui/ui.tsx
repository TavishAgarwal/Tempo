import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { JobState } from "../../state/store";

export function Button({ variant = "default", className = "", ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" }) {
  const v = variant === "primary" ? "bg-primary text-bg border-primary hover:brightness-110" : variant === "danger" ? "border-danger text-danger hover:bg-danger/10" : "bg-raised text-text border-rule hover:border-text";
  return <button {...p} className={`h-9 border px-3 font-mono text-xs uppercase tracking-[0.08em] disabled:opacity-50 ${v} ${className}`} />;
}

const BADGES: Record<JobState, { label: string; cls: string }> = {
  idle: { label: "Idle", cls: "text-muted border-border" },
  solving: { label: "Solving", cls: "text-primary border-primary" },
  safe_plan: { label: "Safe plan", cls: "text-warning border-warning" },
  optimising: { label: "Optimising", cls: "text-primary border-primary" },
  done: { label: "Done", cls: "text-success border-success" },
  error: { label: "Error", cls: "text-danger border-danger" },
  stopped: { label: "Stopped", cls: "text-muted border-border" },
};

export function StatusBadge({ state, extra }: { state: JobState; extra?: string }) {
  const b = BADGES[state];
  return <span role="status" className={`inline-block border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${b.cls}`}>{b.label}{extra ? ` ${extra}` : ""}</span>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block"><span className="panel-title">{label}</span><div className="mt-1.5 text-sm text-text">{children}</div></label>;
}

export function Toast({ text, onClose }: { text: string | null; onClose: () => void }) {
  if (!text) return null;
  return <div role="alert" className="glass tick fixed bottom-4 left-1/2 z-[2000] -translate-x-1/2 px-4 py-2 font-mono text-xs" onClick={onClose}>{text}</div>;
}

export function KpiCard({ label, value, unit, delta, goodWhenDown = true }: { label: string; value: string; unit?: string; delta?: number | null; goodWhenDown?: boolean }) {
  const good = delta == null ? null : goodWhenDown ? delta < 0 : delta > 0;
  return (
    <div className="border border-border bg-bg p-2.5">
      <div className="panel-title">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-1 font-mono text-[26px] leading-none text-text">{value}<span className="text-xs text-muted">{unit}</span></div>
      <div className={`mt-1.5 h-4 font-mono text-[11px] ${good ? "text-primary" : "text-danger"}`}>
        {delta != null && delta !== 0 ? `${delta > 0 ? "▲" : "▼"} ${Math.abs(delta).toFixed(1)}%` : ""}
      </div>
    </div>
  );
}

/** A themed listbox that replaces the OS-drawn <select>: keyboard (arrows, Home/End, Enter, Esc, type to jump) and screen-reader friendly. */
export function Select<T extends string>({ value, onChange, options, label }: { value: T; onChange: (v: T) => void; options: { value: T; label: string; hint?: string }[]; label: string }) {
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const id = useId();
  const cur = options.findIndex((o) => o.value === value);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);
  const show = () => { setHi(Math.max(0, cur)); setOpen(true); };
  const pick = (i: number) => { onChange(options[i].value); setOpen(false); };
  const key = (e: React.KeyboardEvent) => {
    if (!open) { if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); show(); } return; }
    if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(options.length - 1, h + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(0, h - 1)); }
    else if (e.key === "Home") { e.preventDefault(); setHi(0); }
    else if (e.key === "End") { e.preventDefault(); setHi(options.length - 1); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(hi); }
    else if (e.key.length === 1) { const j = options.findIndex((o) => o.label.toLowerCase().startsWith(e.key.toLowerCase())); if (j >= 0) setHi(j); }
    else if (e.key === "Tab") setOpen(false);
  };
  return (
    <div ref={root} className="relative">
      <button type="button" role="combobox" aria-label={label} aria-expanded={open} aria-haspopup="listbox" aria-controls={id} onClick={() => (open ? setOpen(false) : show())} onKeyDown={key}
        className={`flex h-9 w-full items-center justify-between gap-2 border bg-bg px-2.5 text-left text-sm text-text hover:border-text ${open ? "border-primary" : "border-rule"}`}>
        <span className="truncate">{options[cur]?.label ?? "Select"}</span>
        <svg width="10" height="6" viewBox="0 0 10 6" aria-hidden className={`shrink-0 transition-transform ${open ? "rotate-180" : ""}`}><path d="M1 1l4 4 4-4" fill="none" stroke="var(--primary)" strokeWidth="1.6" /></svg>
      </button>
      {open && (
        <ul id={id} role="listbox" aria-label={label} className="absolute inset-x-0 top-full z-[3000] mt-1 max-h-64 overflow-y-auto border border-primary bg-surface py-1 shadow-[0_8px_0_-4px_rgba(0,0,0,.5)]">
          {options.map((o, i) => (
            <li key={o.value} role="option" aria-selected={o.value === value} onMouseEnter={() => setHi(i)} onMouseDown={(e) => { e.preventDefault(); pick(i); }}
              className={`flex cursor-pointer items-center gap-2 px-2.5 py-1.5 text-sm ${i === hi ? "bg-raised text-text" : "text-muted"}`}>
              <span className={`h-1.5 w-1.5 shrink-0 ${o.value === value ? "bg-primary" : "bg-transparent"}`} />
              <span className="min-w-0 flex-1 truncate">{o.label}</span>
              {o.hint && <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted">{o.hint}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
