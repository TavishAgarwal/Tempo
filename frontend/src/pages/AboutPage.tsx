const STEPS = ["Random keys", "Sort into giant tour", "Split by capacity", "VND local search", "Write back to keys", "Update bests", "QPSO update"];

export default function AboutPage() {
  return (
    <div className="mx-auto h-full max-w-3xl space-y-4 overflow-y-auto p-4">
      <h1 className="text-xl font-medium">Tempo: traffic-aware routing</h1>
      <p>Tempo&rsquo;s solver, TA-QPSO, is a quantum-inspired optimiser that runs on a normal CPU. Its QPSO sampling rule is classical. We claim no quantum hardware and no quantum speedup.</p>
      <svg viewBox="0 0 760 120" className="w-full" role="img" aria-label="The seven steps of the solver loop; step 7 is the QPSO update">
        {STEPS.map((s, i) => (
          <g key={s} transform={`translate(${i * 108},30)`}>
            <rect width="100" height="56" rx="0" fill="var(--surface)" stroke={i === 6 ? "var(--primary)" : "var(--border)"} strokeWidth={i === 6 ? 3 : 1} />
            <text x="50" y="22" textAnchor="middle" fontSize="11" fill="var(--text-muted)">{i + 1}</text>
            <text x="50" y="40" textAnchor="middle" fontSize="10" fill="var(--text)">{s}</text>
          </g>
        ))}
      </svg>
      <h2 className="panel-title mt-2 text-text">Model</h2>
      <p>Travel time depends on departure time through stepwise edge speeds (Ichoua–Gendreau–Potvin), which keeps it FIFO: leaving later never gets you there earlier. Capacity is enforced by construction in Split. The objective is total travel time, with distance and congestion exposure normalised by a nearest-neighbour reference. Every plan is scored by an edge-level simulator, and every number comes from a saved run record.</p>
      <h2 className="panel-title mt-2 text-text">Data and licences</h2>
      <ul className="list-disc pl-5"><li>Road network: © OpenStreetMap contributors (ODbL).</li><li>Speed profiles: calibrated time-of-day profile (synthetic).</li><li>Poryos2026 benchmark: ODbL. KAYROS: MIT. Map tiles: CARTO.</li></ul>
      <h2 className="panel-title mt-2 text-text">Limitations</h2>
      <ul className="list-disc pl-5"><li>One depot, one vehicle type, and demands known in advance.</li><li>Traffic is synthetic, not live data.</li><li>Paths between stops are free-flow fastest paths, and are re-routed only for incidents.</li><li>Results against PyVRP are reported as they came out, losses included.</li></ul>
    </div>
  );
}
