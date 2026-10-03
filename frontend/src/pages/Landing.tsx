import { Children, isValidElement, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import Stage from "../gallery/Stage";
import { G, ROOMS } from "../gallery/state";
import { loadLanding, type SceneData } from "../scene/data";
import { M } from "../scene/numbers";
import { startScroll } from "../scene/scroll";
import { useStore } from "../state/store";
import { Mark } from "./stickers";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/700.css";
import "../styles/landing.css";

const f1 = (x: number) => x.toFixed(1);

function openApp() {
  location.hash = "app";
  useStore.getState().set({ page: "plan" });
}

const Mk = ({ children }: { children: ReactNode }) => <span className="mark">{children}</span>;
const Hex = () => <svg className="hexi" viewBox="0 0 12 12" aria-hidden><path d="M6 .6 10.7 3.3v5.4L6 11.4 1.3 8.7V3.3z" /></svg>;

type Tone = "coal" | "slate" | "lime" | "bone" | "coral" | "amber";
interface Room { tone: Tone; name: string; giant: string; lay: string; copy: ReactNode; tags?: [string, number, number][] }

function Kpi({ v, unit, k }: { v: string; unit: string; k: string }) {
  return <div className="kpi"><b>{v}<small>{unit}</small></b><span>{k}</span></div>;
}

/** Splits a room's copy at its heading: everything up to and including the h1/h2 is the head, the rest the body. */
function split(copy: ReactNode) {
  const kids = Children.toArray((isValidElement(copy) ? (copy.props as { children?: ReactNode }).children : copy) as ReactNode);
  const at = kids.findIndex((k) => isValidElement(k) && (k.type === "h1" || k.type === "h2"));
  return [kids.slice(0, at + 1), kids.slice(at + 1)];
}

export default function Landing() {
  const [data, setData] = useState<SceneData | null>(null);
  const [err, setErr] = useState(false);
  const root = useRef<HTMLDivElement>(null), bgT = useRef<HTMLDivElement>(null), fgT = useRef<HTMLDivElement>(null);
  const label = useRef<HTMLSpanElement>(null);

  useEffect(() => { loadLanding().then(setData).catch(() => setErr(true)); }, []);
  useEffect(() => {
    scrollTo(0, 0);
    document.documentElement.classList.add("lp-on");
    const stop = startScroll();
    return () => { stop(); document.documentElement.classList.remove("lp-on"); };
  }, []);

  // one rAF loop moves both tracks in step with the 3D camera and hands every room its position (--rel) and presence (--act)
  useEffect(() => {
    if (!data) return;
    let raf = 0, tone = "", lastName = "";
    const bg = bgT.current, fg = fgT.current, el = root.current;
    if (!bg || !fg || !el) return;
    const bgRooms = Array.from(bg.children) as HTMLElement[], fgRooms = Array.from(fg.children) as HTMLElement[];
    const chips = Array.from(el.querySelectorAll<HTMLElement>(".chip"));
    const hexes = Array.from(el.querySelectorAll<HTMLElement>(".g-hex button"));
    const tick = () => {
      const pos = G.pos, ty = -pos * (bg.parentElement?.clientHeight ?? innerHeight);
      el.style.setProperty("--sk", `${Math.max(-6, Math.min(6, G.vel * 1.1)).toFixed(2)}deg`);
      bg.style.transform = `translate3d(0,${ty}px,0)`;
      fg.style.transform = `translate3d(0,${ty}px,0)`;
      for (let i = 0; i < ROOMS; i++) {
        const rel = pos - i;
        if (Math.abs(rel) > 1.6) continue;
        const act = Math.max(0, 1 - Math.abs(rel));
        for (const r of [bgRooms[i], fgRooms[i]]) { r.style.setProperty("--rel", rel.toFixed(3)); r.style.setProperty("--act", act.toFixed(3)); }
      }
      for (const c of chips) {
        const k = c.dataset.chip ?? "";
        const txt = k === "live" ? `${String(Math.floor(G.hour)).padStart(2, "0")}:00 · main roads at ${Math.round(G.ratio * 100)}% of free flow` : G.chip[Number(k)] ?? "";
        if (c.textContent !== txt) c.textContent = txt;
      }
      const near = Math.min(ROOMS - 1, Math.max(0, Math.round(pos)));
      const t = bgRooms[near]?.dataset.tone ?? "coal";
      if (t !== tone) { tone = t; el.dataset.tone = t; }
      hexes.forEach((h, i) => h.classList.toggle("on", i === near));
      const nm = `${String(near + 1).padStart(2, "0")} / ${ROOMS} · ${bgRooms[near]?.dataset.name ?? ""}`;
      if (nm !== lastName && label.current) { lastName = nm; label.current.textContent = nm; }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [data]);

  if (err) return <div className="landing lp-msg"><p>the landing data is missing. run <code>scripts/export_landing_data.py</code> from <code>backend/</code>.</p><button className="pill" onClick={openApp}>open dashboard</button></div>;
  if (!data) return <div className="landing lp-msg"><p>hanging the exhibits&hellip;</p></div>;

  const d = data, inc = d.incident;
  const arterialPct = Math.round(d.ratioPeak["3"] * 100), localPct = Math.round(d.ratioPeak["5"] * 100);
  const jDrop = (1 - inc.final.J / inc.fallback.J) * 100;

  const rooms: Room[] = [
    { tone: "coal", name: "welcome", giant: "", lay: "hero", tags: [["28.6315° N · 77.2167° E", 40, 9]],  copy: (<>
      <p className="hand">// dear dispatchers</p>
      <h1>routes that keep the clock.</h1>
      <p className="lede">tempo plans delivery routes around the real hour of the day, and it <Mk>actually</Mk> shows its work. every number here comes from a saved run, the wins and the losses.</p>
      <button className="pill" onClick={openApp}>open the dashboard</button>
      <p className="fine">runs on a normal cpu. no quantum hardware needed.</p>
      <p className="chip" data-chip="live" />
    </>) },
    { tone: "lime", name: "the clock", giant: "24h", lay: "clock", tags: [["fig. 02 · speed ratio by hour", 62, 90]],  copy: (<>
      <p className="wall"><Hex />02 &mdash; the clock</p>
      <h2>the same road, 24 hours.</h2>
      <p>each bar is one hour. the outer ring is main roads, the inner ring is side streets, and a bar&rsquo;s length is speed as a share of free flow. at the evening peak main roads fall to <Mk>{arterialPct}%</Mk> and side streets to {localPct}%.</p>
      <p className="quiet">a plan made on a static map is a plan for a city that isn&rsquo;t there. speed profile: calibrated time-of-day profile (synthetic), anchored to tomtom&rsquo;s hourly delhi data.</p>
    </>) },
    { tone: "slate", name: "the parcels", giant: "100", lay: "parcels", tags: [["100 stops · 8 vans", 44, 8]],  copy: (<>
      <p className="wall"><Hex />03 &mdash; the parcels</p>
      <h2>one depot. {d.customers.length} parcels. eight vans.</h2>
      <p>the delhi demo: orders of 1&ndash;9 items, {d.capacity} per van, everyone leaves at 17:30. a parcel&rsquo;s height is its order size and its tape is the van that delivers it, so each colour is one van&rsquo;s round.</p>
      <p className="quiet">{M.graph.junctions.toLocaleString()} junctions and {M.graph.segments.toLocaleString()} road segments from openstreetmap sit underneath. speeds step with the hour, which keeps travel time fifo: leaving later never gets you there earlier.</p>
    </>) },
    { tone: "bone", name: "the route", giant: "routes", lay: "route", tags: [["fig. 04 · one van, replayed", 60, 12]],  copy: (<>
      <p className="wall"><Hex />04 &mdash; the route</p>
      <h2>every route can be replayed.</h2>
      <p className="chip" data-chip="3" />
      <div className="kpis">
        <Kpi v={f1(d.plan.T_min)} unit=" min" k="total travel time" />
        <Kpi v={f1(d.plan.D_km)} unit=" km" k="distance" />
        <Kpi v={f1(d.plan.C_min)} unit=" min" k="on roads below half speed" />
      </div>
      <p>plans are scored by an edge-level simulator, not by the optimiser&rsquo;s own lookup tables. the two differ by about 4&ndash;5% on this instance, and we measured it.</p>
    </>) },
    { tone: "coral", name: "the closure", giant: "18:00", lay: "closure", tags: [["18:00 · zone closed", 6, 84]],  copy: (<>
      <p className="wall"><Hex />05 &mdash; the closure</p>
      <h2>18:00. {inc.segments.length} segments get coned off.</h2>
      <div className="kpis">
        <Kpi v={inc.fallbackLatencyS.toFixed(2)} unit=" s" k="to a safe plan" />
        <Kpi v={String(inc.vehicles.filter((v) => v.status !== "done").length)} unit=" vans" k="still on the road" />
      </div>
      <p>the safe plan keeps every van&rsquo;s remaining stops and re-paths each leg around the closure. vans finish the edge they&rsquo;re on and reach the stop they&rsquo;re committed to; nobody is diverted mid-street. over 90 timed runs the slowest was {M.e4.safePlanMaxS} s.</p>
    </>) },
    { tone: "coal", name: "the recovery", giant: "re-plan", lay: "recovery", tags: [["fig. 06 · before and after", 6, 8]],  copy: (<>
      <p className="wall"><Hex />06 &mdash; the recovery</p>
      <h2>re-optimise, without reshuffling the fleet.</h2>
      <p className="chip" data-chip="5" />
      <div className="kpis">
        <Kpi v={f1(inc.fallback.T_rem_min)} unit=" min" k="remaining, safe plan" />
        <Kpi v={f1(inc.final.T_rem_min)} unit=" min" k={`remaining, re-planned (−${jDrop.toFixed(1)}% cost)`} />
      </div>
      <p>{inc.moved.length} parcels change vans. a stability penalty cuts that to {M.e4.movedAfterMu} at no cost in quality (j {M.e4.jBeforeMu} &rarr; {M.e4.jAfterMu}). a pyvrp re-solve from the same snapshot came out {M.e4.pyvrpWorsePct}% worse, though that baseline is our own approximate adaptation. a static re-solve was a touch better ({M.e4.staticResolvePct}% vs {M.e4.warmPct}%), and we report it.</p>
    </>) },
    { tone: "amber", name: "the solver", giant: "7 steps", lay: "solver", copy: (<>
      <p className="wall"><Hex />07 &mdash; the solver</p>
      <h2>what actually does the work.</h2>
      <ol className="steps">
        {["random keys", "sort into a giant tour", "split by capacity", "vnd local search", "write back to keys", "update bests", "qpso update"].map((s, n) => <li key={s} className={n === 3 ? "hot" : n === 6 ? "ghost" : ""}><b>{n + 1}</b>{s}</li>)}
      </ol>
      <p>the qpso step (the dotted hexagon) is a sampling rule that runs on a normal cpu. no quantum hardware, no speedup claimed. at equal budget it beats pso and random restarts from n = {M.e2.beatsPsoRandomFromN} up and ties ga to n = {M.e2.tiesGaUpToN}; a small step was the fix, worth <Mk>{M.e2.vsFirstRoundPct[0]}&ndash;{M.e2.vsFirstRoundPct[1]}%</Mk> over the first version. removing the vnd step, the tall black one, raises cost by <Mk>{M.e2.vndRaisesJPct[0]}&ndash;{M.e2.vndRaisesJPct[1]}%</Mk>.</p>
    </>) },
    { tone: "bone", name: "the score", giant: "gap 0", lay: "score",  copy: (<>
      <p className="wall"><Hex />08 &mdash; the score</p>
      <h2>exact where we can check, behind where we can&rsquo;t.</h2>
      <div className="label"><div><small>name</small>tempo</div><div><small>class</small>time-dependent vrp</div><div><small>checked against</small>milp &middot; cvrplib &middot; poryos</div></div>
      <table className="tbl"><tbody>
        <tr><td>milp optimum, {M.e1.milpInstances} random n=10</td><td>gap {M.e1.milpGapPct}</td></tr>
        <tr><td>cvrplib best-known, {M.e1.bksMatched} of {M.e1.bksTotal}</td><td>matched</td></tr>
        <tr><td>cvrplib x-n101-k25</td><td>+{M.e1.xn101GapPct}%</td></tr>
        <tr><td>poryos2026 tdvrptw, {M.poryos.instances} instances</td><td>matches {M.poryos.matchedBks}</td></tr>
        <tr><td>pyvrp at n = 500 (cost, lower is better)</td><td>{M.e2.n500.pyvrp} vs {M.e2.n500.qpso}</td></tr>
        <tr><td>ga at n = 500 (cost, lower is better)</td><td>{M.e2.n500.ga} vs {M.e2.n500.qpso}</td></tr>
      </tbody></table>
      <p className="quiet">pyvrp beats us from n &ge; 100 and ga from n &ge; 200. we don&rsquo;t claim otherwise.</p>
    </>) },
    { tone: "slate", name: "honestly", giant: "~0.5%", lay: "honest", tags: [["static vs time-aware", 58, 90]], copy: (<>
      <p className="wall"><Hex />09 &mdash; does time-awareness pay?</p>
      <h2>honestly: a little.</h2>
      <p>the grey bar is a static plan, the lime one a time-dependent plan. planning with the hour in mind shortens the 17:30 run by {M.e3.reductionPct[0]}&ndash;{M.e3.reductionPct[1]}%. after multiple-test correction that isn&rsquo;t significant (holm p = {M.e3.holmP[0]} and {M.e3.holmP[1]}). the real delhi profile is flat enough that the clock changes little.</p>
      <p className="quiet">the system&rsquo;s value is the pipeline and the incident response, not this number.</p>
    </>) },
    { tone: "coal", name: "not yet", giant: "not yet", lay: "notyet", copy: (<>
      <p className="wall"><Hex />10 &mdash; what we haven&rsquo;t done</p>
      <h2>only tested on the past.</h2>
      <p>the wireframe is what&rsquo;s still unbuilt. the traffic profile is synthetic, there&rsquo;s no field trial, one depot, one vehicle type, and demands known in advance. emission coefficients are illustrative. nobody has rehearsed the spoken demo yet. at n = 500 the lookup tables take {M.e5.tablesMb} mb and the process peaks at {M.e5.rssMb} mb.</p>
      <div className="tags"><span>not yet field-tested</span><span>synthetic traffic</span><span>single depot</span><span>quantum-inspired = classical</span><span>emissions illustrative</span></div>
    </>) },
    { tone: "lime", name: "in one line", giant: "tempo", lay: "final", tags: [["tempo / delhi", 52, 90]],  copy: (<>
      <p className="hand">// 11 · in one line</p>
      <h2 className="final">plan for the clock. prove the route. re&#8209;plan before the next van turns.</h2>
      <button className="pill" onClick={openApp}>open the dashboard</button>
      <p className="fine">road network &copy; openstreetmap contributors (odbl). speed profile: calibrated time-of-day profile (synthetic).</p>
    </>) },
  ];

  const go = (i: number) => scrollTo({ top: (i / (ROOMS - 1)) * (document.documentElement.scrollHeight - innerHeight), behavior: "smooth" });

  return (
    <div className="landing" ref={root} data-tone="coal">
      <div className="runway">
        <div className="pin">
          <div className="track bgT" ref={bgT}>
            {rooms.map((r, i) => (
              <div key={i} className="rbg" data-tone={r.tone} data-name={r.name}>
                {i === 0 ? <div className="wordmark" aria-hidden>Tempo</div> : r.giant && <div className="giant" aria-hidden>{r.giant}</div>}
                {r.lay === "closure" && <div className="tape" aria-hidden>{"ROAD CLOSED · ".repeat(14)}</div>}
              </div>
            ))}
          </div>
          <Stage data={d} />
          <div className="track fgT" ref={fgT}>
            {rooms.map((r, i) => (
              <section key={i} className={`room lay-${r.lay}`} data-tone={r.tone} aria-label={r.name}>
                <div className="copy"><div className="head">{split(r.copy)[0]}</div><div className="body">{split(r.copy)[1]}</div></div>
                {r.tags?.map(([t, x, y], n) => <span key={n} className="fsw" style={{ left: `${x}%`, top: `${y}%` } as CSSProperties}>{t}</span>)}
              </section>
            ))}
          </div>

          <header className="g-top">
            <a className="g-brand" href="#top" aria-label="Tempo, back to the start" onClick={(e) => { e.preventDefault(); go(0); }}><Mark /></a>
            <button className="pill sm" onClick={openApp}>open dashboard</button>
          </header>
          <nav className="g-hex" aria-label="Rooms">
            {rooms.map((r, i) => (
              <button key={i} aria-label={`Go to ${r.name}`} onClick={() => go(i)}>
                <svg viewBox="0 0 12 12" aria-hidden><path d="M6 .8 10.5 3.4v5.2L6 11.2 1.5 8.6V3.4z" /></svg>
              </button>
            ))}
          </nav>
          <p className="g-count"><span ref={label} /></p>
        </div>
      </div>
    </div>
  );
}
