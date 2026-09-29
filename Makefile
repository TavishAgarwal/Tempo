PY := backend/.venv/bin/python
RUN := cd backend &&

.PHONY: exp-e2-large exp-poryos demo-offline live-snapshot setup data build-graph test lint typecheck run-api run-ui exp-all exp-e1 exp-e2 exp-e3 exp-e4 exp-e5 openapi
setup:
	uv venv --python 3.11 backend/.venv
	uv pip install --python $(PY) -e "backend[dev,build]"
	cd frontend && npm ci

data: build-graph
	$(RUN) .venv/bin/python -m taqpso.bench.fetch_data
	$(RUN) .venv/bin/python -m taqpso.bench.make_scenarios

live-snapshot:
	$(RUN) .venv/bin/python -m taqpso.bench.tomtom

build-graph:
	$(RUN) .venv/bin/python -m taqpso.graph.builder

test:
	$(RUN) .venv/bin/python -m pytest -m "not slow"

lint:
	$(RUN) .venv/bin/ruff check taqpso tests experiments && .venv/bin/mypy
	$(RUN) .venv/bin/lint-imports

run-api:
	$(RUN) NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/uvicorn taqpso.api.main:app --port 8000

run-ui:
	cd frontend && npm run dev

exp-e1: ; $(RUN) .venv/bin/python -m experiments.e1_correctness
exp-e2: ; $(RUN) .venv/bin/python -m experiments.e2_qpso_vs_classical
exp-e3: ; $(RUN) .venv/bin/python -m experiments.e3_traffic_value
exp-e4:
	$(RUN) .venv/bin/python -m experiments.e4_incident
	$(RUN) .venv/bin/python -m experiments.e4_latency
exp-e2-large: ; $(RUN) .venv/bin/python -m experiments.e2_qpso_vs_classical e2_large
exp-e5: ; $(RUN) .venv/bin/python -m experiments.e5_scaling
exp-all: exp-e1 exp-e2 exp-e3 exp-e4 exp-e5

exp-poryos:
	$(RUN) .venv/bin/python -m experiments.poryos_check
	$(RUN) .venv/bin/python -m experiments.poryos_ref TDVRPTW 10 3 10,25

openapi:
	$(RUN) .venv/bin/python -m taqpso.api.export_openapi ../frontend/openapi.json

# Phase 7 gate: demo twice in a row, with a guard that refuses every non-loopback connection.
demo-offline:
	cd backend && TAQPSO_OFFLINE=1 PYTHONPATH=../scripts/offline_guard NUMBA_NUM_THREADS=1 .venv/bin/uvicorn taqpso.api.main:app --port 8000 & \
	API_PID=$$!; sleep 25; $(PY) scripts/demo_check.py --runs 2; STATUS=$$?; kill $$API_PID; exit $$STATUS
