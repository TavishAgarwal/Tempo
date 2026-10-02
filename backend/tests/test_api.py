from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from taqpso.api.main import app
from taqpso.bench.make_scenarios import SCEN

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not (SCEN / "delhi_n30.json").exists(), reason="run `make data`"),
]


def wait(c: TestClient, job: str, timeout: float = 60) -> dict:  # type: ignore[type-arg]
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = c.get(f"/jobs/{job}").json()
        if d["state"] in ("done", "error", "stopped"):
            return d  # type: ignore[no-any-return]
        time.sleep(0.5)
    raise TimeoutError


def test_end_to_end_solve_stream_incident_path_rescore():
    with TestClient(app) as c:
        assert any(s["name"] == "delhi_n30" for s in c.get("/scenarios").json())
        job = c.post("/solve", json={"instance_id": "delhi_n30", "budget_s": 3, "seed": 0}).json()[
            "job_id"
        ]
        with c.websocket_connect(f"/jobs/{job}/stream") as ws:
            msgs = []
            while True:
                m = ws.receive_json()
                msgs.append(m)
                if m["type"] in ("done", "error"):
                    break
        assert any(m["type"] == "improvement" for m in msgs) and msgs[-1]["type"] == "done"
        d = wait(c, job)
        assert d["state"] == "done" and d["run_id"]
        routes = d["solution"]["routes"]
        assert sorted(x for r in routes for x in r) == list(range(1, 31))
        em = c.get(f"/jobs/{job}/emissions").json()
        assert em["kg"] > 0 and "illustrative" in em["label"]
        r = c.post(f"/jobs/{job}/rescore", params={"depart": 10 * 3600}).json()
        assert r["metrics"]["T"] > 0
        inc = c.post(
            "/incidents",
            json={
                "job_id": job,
                "polygon": [[77.20, 28.62], [77.215, 28.62], [77.215, 28.635], [77.20, 28.635]],
                "factor": 0.1,
                "t_start": 64800,
                "t_end": 68400,
                "budget_s": 2,
            },
        ).json()
        with c.websocket_connect(f"/jobs/{inc['job_id']}/stream") as ws:
            first = ws.receive_json()
            while first["type"] == "state":
                first = ws.receive_json()
            assert first["type"] == "fallback" and first["latency_s"] < 1.0  # G4
        assert wait(c, inc["job_id"])["state"] == "done"
        p = c.get(
            "/paths",
            params={
                "from_lon": 77.2,
                "from_lat": 28.62,
                "to_lon": 77.22,
                "to_lat": 28.64,
                "depart": 64800,
            },
        ).json()
        assert p["travel_s"] > 0 and len(p["geometry"]) > 1
        assert c.get("/congestion", params={"slot": 70}).json()["edges"]
        assert c.get("/results").status_code == 200


def test_live_endpoint_and_live_solve():
    from taqpso.config import DATA_DIR

    snap = DATA_DIR / "processed" / "tomtom_snapshot.json"
    with TestClient(app) as c:
        d = c.get("/live").json()
        if not snap.exists():
            assert d["available"] is False
            pytest.skip("no TomTom snapshot (run `make live-snapshot`)")
        assert d["available"] and set(d["ratios"]) >= {"primary", "residential"}
        assert "Live traffic" in d["label"]
        job = c.post(
            "/solve", json={"instance_id": "delhi_n30", "budget_s": 2, "seed": 0, "live": True}
        ).json()["job_id"]
        r = wait(c, job)
        assert r["state"] == "done", r


def test_finished_job_elapsed_is_frozen_and_names_cannot_overwrite():
    with TestClient(app) as c:
        job = c.post("/solve", json={"instance_id": "delhi_n30", "budget_s": 1}).json()["job_id"]
        e1 = wait(c, job)["elapsed_s"]
        time.sleep(1.0)
        assert c.get(f"/jobs/{job}").json()["elapsed_s"] == e1
        body = {
            "name": "delhi_n30",
            "depot_lon": 77.2,
            "depot_lat": 28.6,
            "customers": [{"lon": 77.21, "lat": 28.63, "demand": 1}],
            "capacity": 5,
        }
        assert c.post("/instances", json=body).status_code == 409


def test_incident_is_not_queued_behind_long_solves():
    with TestClient(app) as c:
        base = c.post("/solve", json={"instance_id": "delhi_n30", "budget_s": 1}).json()["job_id"]
        assert wait(c, base)["state"] == "done"
        busy = [
            c.post("/solve", json={"instance_id": "delhi_n30", "budget_s": 20}).json()["job_id"]
            for _ in range(2)
        ]
        t0 = time.time()
        inc = c.post(
            "/incidents",
            json={
                "job_id": base,
                "edges": [10, 11, 12],
                "t_start": 63600,
                "t_end": 67200,
                "budget_s": 1,
            },
        ).json()["job_id"]
        while c.get(f"/jobs/{inc}").json()["state"] == "solving":
            assert time.time() - t0 < 10, "incident waited for a solve worker"
            time.sleep(0.1)
        for j in busy:
            c.post(f"/jobs/{j}/stop")
        for j in busy:
            assert wait(c, j)["state"] in ("stopped", "done")
