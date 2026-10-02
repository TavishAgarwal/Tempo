import { useEffect, useState } from "react";
import { Toast } from "./components/ui/ui";
import AboutPage from "./pages/AboutPage";
import BenchmarkPage from "./pages/BenchmarkPage";
import IncidentPage from "./pages/IncidentPage";
import PathPage from "./pages/PathPage";
import Landing from "./pages/Landing";
import PlanPage from "./pages/PlanPage";
import { loadScenarios } from "./state/actions";
import { pretty } from "./lib";
import { useStore, type Page } from "./state/store";

const TABS: [Page, string][] = [["plan", "Plan"], ["incident", "Incident"], ["benchmark", "Benchmarks"], ["path", "Path"], ["about", "About"]];

function Clock() {
  const [t, setT] = useState(() => new Date());
  useEffect(() => { const i = setInterval(() => setT(new Date()), 1000); return () => clearInterval(i); }, []);
  return <span className="whitespace-nowrap text-muted">IST <b className="font-medium text-text">{t.toLocaleTimeString("en-GB", { timeZone: "Asia/Kolkata" })}</b></span>;
}

export default function App() {
  const { page, set, offline, tilesOffline, toast, scenario, log, logOpen } = useStore();
  useEffect(() => { void loadScenarios(); }, []);
  useEffect(() => { if (toast) { const t = setTimeout(() => set({ toast: null }), 3500); return () => clearTimeout(t); } }, [toast, set]);
  if (page === "landing") return <Landing />;
  return (
    <div className="flex h-screen flex-col gap-2 p-2 font-sans">
      <header className="glass tick flex h-12 shrink-0 items-stretch gap-4 pl-3 pr-3 sm:gap-5">
        <button className="flex items-center gap-2 whitespace-nowrap font-mono text-sm font-medium tracking-[0.2em] text-text" title="Back to the overview" onClick={() => { history.replaceState(null, "", location.pathname); set({ page: "landing" }); }}>
          <svg width="18" height="18" viewBox="0 0 12 12" aria-hidden><path d="M6 .6 10.7 3.3v5.4L6 11.4 1.3 8.7V3.3z" fill="none" stroke="var(--primary)" strokeWidth="1.2" /><path d="M6 3.4v5.2M3.8 6h4.4" stroke="var(--primary)" strokeWidth="1.2" /></svg>TEMPO
        </button>
        <span className="hidden items-center whitespace-nowrap border-l border-border pl-4 font-mono text-[11px] tracking-[0.12em] text-muted xl:flex">DELHI · CONNAUGHT PLACE</span>
        <nav className="flex min-w-0 items-stretch overflow-x-auto" aria-label="Pages">
          {TABS.map(([k, label], n) => (
            <button key={k} onClick={() => set({ page: k })} aria-current={page === k} className={`flex shrink-0 items-center gap-2 border-b-2 px-3.5 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors ${page === k ? "border-primary bg-raised text-text" : "border-transparent text-muted hover:text-text"}`}>
              <span className={page === k ? "text-primary" : "text-muted"}>{String(n + 1).padStart(2, "0")}</span>{label}
            </button>
          ))}
        </nav>
        <span className="ml-auto hidden items-center gap-4 font-mono text-[11px] tracking-wider sm:flex">
          <span className="whitespace-nowrap text-muted">SCN <b className="font-medium text-text">{scenario ? pretty(scenario) : "–"}</b></span>
          <Clock />
          <span className="flex items-center gap-2 whitespace-nowrap border border-border px-2 py-1"><i className={offline ? "h-2 w-2 bg-warning" : "dot-live"} /><span className={offline ? "text-warning" : "text-primary"}>{offline ? "OFFLINE" : "LINK OK"}</span></span>
        </span>
      </header>
      {offline && <div role="status" className="bg-surface px-4 py-1 text-sm text-warning">Offline mode — using saved scenarios</div>}
      {tilesOffline && <div role="status" className="bg-surface px-4 py-1 text-sm text-warning">Map tiles unavailable offline — routes and plans are still shown</div>}
      <div className="min-h-0 flex-1 overflow-hidden">
        {page === "plan" && <PlanPage />}
        {page === "incident" && <IncidentPage />}
        {page === "benchmark" && <BenchmarkPage />}
        {page === "path" && <PathPage />}
        {page === "about" && <AboutPage />}
      </div>
      <footer className="glass shrink-0 px-3 py-1 font-mono text-[11px] text-muted">
        <button className="underline" onClick={() => set({ logOpen: !logOpen })}>{logOpen ? "Hide" : "Show"} solver log ({log.length})</button>
        {logOpen && <pre className="mt-1 max-h-28 overflow-y-auto font-mono">{log.join("\n")}</pre>}
      </footer>
      <Toast text={toast} onClose={() => set({ toast: null })} />
    </div>
  );
}
