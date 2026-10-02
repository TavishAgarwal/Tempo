"""Job manager: process pools (one job = one process, one thread) + per-job message log.

Incidents run in their own pool so a long solve never delays the safe plan.
"""

from __future__ import annotations

import multiprocessing as mp
import threading
import time
import uuid
from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from taqpso.api import worker


@dataclass
class Job:
    id: str
    kind: str
    spec: dict[str, Any]
    created: float = field(default_factory=time.time)
    state: str = "idle"
    messages: list[dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    stop: Any = None
    started: float = 0.0
    ended: float = 0.0

    def best(self) -> dict[str, Any] | None:
        for m in reversed(self.messages):
            if m["type"] in ("done", "improvement", "fallback") and "routes" in m:
                return dict(m)
        return None

    def final(self) -> dict[str, Any] | None:
        for m in reversed(self.messages):
            if m["type"] in ("done", "error"):
                return dict(m)
        return None


class JobManager:
    def __init__(self, solve_workers: int = 2, incident_workers: int = 1) -> None:
        self._ctx = mp.get_context("spawn")
        self._mgr = self._ctx.Manager()
        self._pools = {
            kind: ProcessPoolExecutor(n, mp_context=self._ctx, initializer=worker.warmup)
            for kind, n in (("solve", solve_workers), ("incident", incident_workers))
        }
        for _ in range(incident_workers):  # spawn workers start lazily; warm these up front
            self._pools["incident"].submit(worker.ready)
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, kind: str, spec: dict[str, Any]) -> Job:
        job = Job(uuid.uuid4().hex[:12], kind, spec, stop=self._mgr.Event())
        job.started = time.time()
        job.state = "solving"
        q = self._mgr.Queue()
        fn = worker.solve_job if kind == "solve" else worker.incident_job
        fut = self._pools[kind].submit(fn, spec, q, job.stop)
        fut.add_done_callback(lambda f: self._on_exit(f, q))
        with self._lock:
            self.jobs[job.id] = job
        threading.Thread(target=self._drain, args=(job, q), daemon=True).start()
        return job

    @staticmethod
    def _on_exit(fut: Future[Any], q: Any) -> None:
        """A worker that dies or raises before posting its final message must still end the job."""
        if not fut.cancelled() and fut.exception() is None:
            return
        cause = "cancelled" if fut.cancelled() else f"{fut.exception()!r}"
        try:
            q.put({"type": "error", "message": f"Job worker failed: {cause}"})
        except Exception:  # noqa: BLE001 - the manager is gone during shutdown
            pass

    def _drain(self, job: Job, q: Any) -> None:
        while True:
            try:
                msg = q.get()
            except (EOFError, OSError):  # manager shut down with the job still running
                return
            with self._lock:
                job.messages.append(msg)
                t = msg["type"]
                if t == "state":
                    job.state = msg["state"]
                elif t == "fallback":
                    job.state = "safe_plan"
                elif t == "improvement":
                    job.state = "optimising" if job.kind == "incident" else "solving"
                elif t == "done":
                    job.state = "stopped" if msg.get("stopped") else "done"
                    job.ended, job.finished = time.time(), True
                elif t == "error":
                    job.state = "error"
                    job.ended, job.finished = time.time(), True
            if job.finished:
                return

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def stop(self, job_id: str) -> bool:
        j = self.jobs.get(job_id)
        if j is None:
            return False
        j.stop.set()
        return True

    def shutdown(self) -> None:
        for pool in self._pools.values():
            pool.shutdown(wait=False, cancel_futures=True)
        self._mgr.shutdown()
