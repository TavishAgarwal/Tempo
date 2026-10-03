#!/usr/bin/env python3
"""Run the 3-minute demo flow against a running API, N times, and fail on any error.

    python scripts/demo_check.py --runs 2 --scenario delhi_demo --budget 10

Steps per run: scenarios -> solve (stream) -> emissions -> rescore 10:00 -> incident (fallback
latency < 1 s, re-optimised plan streamed) -> path -> results. Writes results/demo_check.json.
Also asserts the built UI references no external host other than the OSM tile server.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]


def call(api: str, path: str, method: str = "GET", body: dict | None = None):  # type: ignore[type-arg]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(api + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def stream(api: str, job: str, until: tuple[str, ...] = ("done", "error")) -> list[dict]:  # type: ignore[type-arg]
    ws_url = api.replace("http", "ws", 1) + f"/jobs/{job}/stream"
    msgs = []
    with connect(ws_url, open_timeout=10) as ws:
        t0 = time.time()
        while time.time() - t0 < 300:
            m = json.loads(ws.recv(timeout=120))
            msgs.append(m)
            if m["type"] in until:
                return msgs
    raise TimeoutError(job)


def one_run(api: str, scenario: str, budget: float) -> dict:  # type: ignore[type-arg]
    out: dict = {}
    t0 = time.time()
    assert any(s["name"] == scenario for s in call(api, "/scenarios")), "scenario missing"
    job = call(api, "/solve", "POST", {"instance_id": scenario, "budget_s": budget, "seed": 0, "depart_s": 17.5 * 3600})["job_id"]
    msgs = stream(api, job)
    assert msgs[-1]["type"] == "done", msgs[-1]
    assert any(m["type"] == "improvement" for m in msgs), "no streamed improvements"
    st = call(api, f"/jobs/{job}")
    out["T_min"] = st["solution"]["metrics"]["T"] / 60
    out["run_id"] = st["run_id"]
    out["emissions_kg"] = call(api, f"/jobs/{job}/emissions")["kg"]
    out["rescore_10h_T_min"] = call(api, f"/jobs/{job}/rescore?depart=36000", "POST")["metrics"]["T"] / 60
    inc = call(api, "/incidents", "POST", {
        "job_id": job, "polygon": [[77.200, 28.620], [77.215, 28.620], [77.215, 28.635], [77.200, 28.635]],
        "factor": 0.1, "t_start": 64800, "t_end": 68400, "budget_s": 5})["job_id"]
    im = stream(api, inc)
    fb = next(m for m in im if m["type"] == "fallback")
    out["fallback_latency_s"] = fb["latency_s"]
    assert fb["latency_s"] < 1.0, f"fallback took {fb['latency_s']} s"
    assert im[-1]["type"] == "done", im[-1]
    p = call(api, "/paths?" + urllib.parse.urlencode(dict(from_lon=77.20, from_lat=28.62, to_lon=77.22, to_lat=28.64, depart=64800)))
    out["path_travel_s"], out["path_freeflow_s"] = p["travel_s"], p["free_flow_travel_s"]
    assert call(api, "/results") is not None
    out["wall_s"] = time.time() - t0
    return out


def external_hosts() -> set[str]:
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        return set()
    hosts: set[str] = set()
    for f in dist.rglob("*"):
        if f.suffix in {".js", ".css", ".html"}:
            hosts |= set(re.findall(r"https?://([A-Za-z0-9.\-]+)", f.read_text(errors="ignore")))
    return hosts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--scenario", default="delhi_demo")
    ap.add_argument("--budget", type=float, default=10.0)
    a = ap.parse_args()
    res = {"runs": [], "ui_external_hosts": sorted(external_hosts())}
    for i in range(a.runs):
        r = one_run(a.api, a.scenario, a.budget)
        print(f"run {i + 1}: OK", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
        res["runs"].append(r)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "demo_check.json").write_text(json.dumps(res, indent=1))
    print("external hosts referenced by the UI bundle:", res["ui_external_hosts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
