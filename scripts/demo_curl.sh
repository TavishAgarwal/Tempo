#!/usr/bin/env bash
# End-to-end API demo: scenario -> solve -> poll -> incident (fallback + improvements) -> path query.
set -euo pipefail
API=${API:-http://localhost:8000}
j() { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"; }

echo "== scenarios"; curl -s $API/scenarios | j "[s['name'] for s in d]"
JOB=$(curl -s -X POST $API/solve -H 'Content-Type: application/json' \
  -d '{"instance_id":"delhi_n30","solver":"qpso","preset":"fastest","budget_s":5,"seed":0}' | j "d['job_id']")
echo "== solve job $JOB"
until [ "$(curl -s $API/jobs/$JOB | j "d['state']")" = "done" ]; do sleep 1; done
curl -s $API/jobs/$JOB | j "d['solution']['metrics']"
echo "== incident (blocks the busiest corridor polygon)"
INC=$(curl -s -X POST $API/incidents -H 'Content-Type: application/json' \
  -d '{"job_id":"'$JOB'","polygon":[[77.200,28.620],[77.215,28.620],[77.215,28.635],[77.200,28.635]],"factor":0.1,"t_start":64800,"t_end":68400,"budget_s":5}' | j "d['job_id']")
echo "incident job $INC"
until [ "$(curl -s $API/jobs/$INC | j "d['state']")" = "done" ]; do sleep 1; done
curl -s $API/jobs/$INC | j "d['solution']['metrics']"
echo "== time-dependent path"
curl -s "$API/paths?from_lon=77.20&from_lat=28.62&to_lon=77.22&to_lat=28.64&depart=64800" | j "(d['travel_s'], d['free_flow_travel_s'])"
