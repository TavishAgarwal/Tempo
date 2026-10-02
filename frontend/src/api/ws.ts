export type StreamMsg = {
  type: "state" | "improvement" | "fallback" | "done" | "error";
  state?: string;
  t?: number;
  cost?: number;
  routes?: number[][];
  geometry?: number[][][];
  metrics?: Record<string, number | number[]>;
  fallback_metrics?: Record<string, number | number[]>;
  vehicles?: { vehicle: number; status: string; lon: number; lat: number; committed: number; eta_s: number }[];
  moved?: { customer: number; from: number; to: number }[];
  latency_s?: number;
  reopt_s?: number;
  run_id?: string;
  message?: string;
  diversity?: number;
  depart?: number;
};

/** Subscribe to a job stream; reconnects (replaying from the start) until the job finishes. */
export function openStream(jobId: string, onMsg: (m: StreamMsg) => void): () => void {
  let closed = false;
  let seen = 0;
  const connect = () => {
    if (closed) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/jobs/${jobId}/stream`);
    let n = 0;
    ws.onmessage = (e) => {
      n += 1;
      if (n <= seen) return; // replayed message already handled
      seen = n;
      const m = JSON.parse(e.data) as StreamMsg;
      onMsg(m);
      if (m.type === "done" || m.type === "error") closed = true;
    };
    ws.onclose = () => { if (!closed) setTimeout(connect, 800); };
  };
  connect();
  return () => { closed = true; };
}
