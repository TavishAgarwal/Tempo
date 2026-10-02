from __future__ import annotations

import queue
from concurrent.futures import Future
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from taqpso.api import worker
from taqpso.api.jobs import JobManager
from taqpso.api.main import app
from taqpso.api.schemas import InstanceCreate


def _spec(**kw: Any) -> dict[str, Any]:
    return {
        "instance_id": "no_such_scenario",
        "solver": "qpso",
        "preset": "fastest",
        "budget_s": 1.0,
        "seed": 0,
        "depart_s": None,
        "live": False,
        **kw,
    }


def test_solve_job_reports_setup_failure_as_error() -> None:
    # a failure before the solver starts (here: missing scenario) must still end the job
    q: queue.Queue[dict[str, Any]] = queue.Queue()
    out = worker.solve_job(_spec(), q, None)
    assert out["type"] == "error"
    assert q.get_nowait() == out


def test_worker_exit_without_final_message_posts_error() -> None:
    q: queue.Queue[dict[str, Any]] = queue.Queue()
    f: Future[Any] = Future()
    f.set_exception(RuntimeError("worker died"))
    JobManager._on_exit(f, q)
    m = q.get_nowait()
    assert m["type"] == "error" and "worker died" in m["message"]

    ok: Future[Any] = Future()
    ok.set_result({"type": "done"})
    JobManager._on_exit(ok, q)
    assert q.empty()


@pytest.mark.parametrize("name", ["../x", "/tmp/x", "a/b", "a.b", "", "x" * 65])
def test_instance_name_must_be_a_plain_identifier(name: str) -> None:
    with pytest.raises(ValidationError):
        InstanceCreate(
            name=name,
            depot_lon=77.2,
            depot_lat=28.6,
            customers=[{"lon": 77.21, "lat": 28.63, "demand": 1}],
            capacity=5,
        )


def test_create_instance_rejects_path_names() -> None:
    body = {
        "name": "../../escape",
        "depot_lon": 77.2,
        "depot_lat": 28.6,
        "customers": [{"lon": 77.21, "lat": 28.63, "demand": 1}],
        "capacity": 5,
    }
    assert TestClient(app).post("/instances", json=body).status_code == 422
