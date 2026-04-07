#!/usr/bin/env python3
"""
test_validator.py — Local simulation of OpenEnv Phase 2 validator.
Run this BEFORE pushing to HF to catch any issues.

Usage:
  1. Start the server:  uvicorn main:app --host 0.0.0.0 --port 7860
  2. In another terminal: python test_validator.py
"""

import requests
import sys

BASE_URL = "http://localhost:7860"
TASK_IDS = ["task_easy", "task_medium", "task_hard"]
PASS  = "\033[92m[PASS]\033[0m"
FAIL  = "\033[91m[FAIL]\033[0m"

errors = []

def check(condition, label, detail=""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}" + (f" — {detail}" if detail else ""))
        errors.append(label)

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ── Best-case actions (perfect answers) ──────────────────────
BEST_ACTIONS = {
    "task_easy": {
        "checks_requested": ["check_rollback", "check_destructive"],
        "severity": "high",
        "recommendation": "request_changes",
        "reasoning": "Destructive op, no rollback, small non-prod table."
    },
    "task_medium": {
        "checks_requested": ["check_nullability", "check_rollback", "check_lock_risk"],
        "severity": "critical",
        "recommendation": "block",
        "reasoning": "NOT NULL without DEFAULT on production table."
    },
    "task_hard": {
        "checks_requested": ["check_lock_risk", "check_index_safety", "check_rollback"],
        "severity": "critical",
        "recommendation": "escalate",
        "reasoning": "Blocking index on 4.2M row production table."
    },
}

# ── Worst-case action (all wrong) ────────────────────────────
WORST_ACTION = {
    "checks_requested": [],
    "severity": "safe",
    "recommendation": "approve",
    "reasoning": ""
}

# ══════════════════════════════════════════════════════════════
section("Phase 1 — Health check")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    check(r.status_code == 200, f"GET /health → 200", f"got {r.status_code}")
    check("status" in r.json(), "/health response has 'status' field")
except Exception as e:
    check(False, "Server reachable", str(e))
    print(f"\n{FAIL} Server not running. Start it with:")
    print("       uvicorn main:app --host 0.0.0.0 --port 7860")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════
section("Phase 2 — Reset endpoint")
for task_id in TASK_IDS:
    r = requests.post(f"{BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
    check(r.status_code == 200, f"POST /reset task={task_id} → 200", f"got {r.status_code}")
    body = r.json()
    check("done" in body,        f"  [{task_id}] reset has 'done' field")
    check(body.get("done") == False, f"  [{task_id}] done=false after reset")
    check("observation" in body, f"  [{task_id}] reset has 'observation'")
    obs = body.get("observation", {})
    check(obs.get("task_id") == task_id, f"  [{task_id}] observation.task_id correct")
    check("migration_sql" in obs,  f"  [{task_id}] observation has 'migration_sql'")
    check("signals" in obs,        f"  [{task_id}] observation has 'signals'")
    reward = body.get("reward")
    check(reward is None, f"  [{task_id}] reset reward is null (not a float)", f"got {reward}")

# ══════════════════════════════════════════════════════════════
section("Phase 2 — Step: score strictly in (0, 1) — best-case actions")
for task_id in TASK_IDS:
    requests.post(f"{BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
    action = BEST_ACTIONS[task_id]
    r = requests.post(f"{BASE_URL}/step", json=action, timeout=10)
    check(r.status_code == 200, f"POST /step task={task_id} → 200", f"got {r.status_code}")
    body = r.json()
    reward = body.get("reward")
    check(isinstance(reward, (int, float)), f"  [{task_id}] reward is numeric", f"got {type(reward)}")
    if isinstance(reward, (int, float)):
        check(0 < reward < 1, f"  [{task_id}] reward in (0,1) → {reward}",
              f"reward={reward} violates 0 < score < 1")
    check(body.get("done") == True, f"  [{task_id}] done=true after step")

# ══════════════════════════════════════════════════════════════
section("Phase 2 — Step: score strictly in (0, 1) — worst-case actions")
for task_id in TASK_IDS:
    requests.post(f"{BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
    r = requests.post(f"{BASE_URL}/step", json=WORST_ACTION, timeout=10)
    reward = r.json().get("reward")
    if isinstance(reward, (int, float)):
        check(0 < reward < 1, f"  [{task_id}] worst-case reward in (0,1) → {reward}",
              f"reward={reward} — validator rejects 0.0 and 1.0")

# ══════════════════════════════════════════════════════════════
section("Phase 2 — Robustness: step before reset")
r = requests.post(f"{BASE_URL}/step", json=BEST_ACTIONS["task_easy"], timeout=10)
check(r.status_code == 200, "POST /step before /reset doesn't crash", f"got {r.status_code}")

# ══════════════════════════════════════════════════════════════
section("Phase 2 — State endpoint")
r = requests.get(f"{BASE_URL}/state", timeout=10)
check(r.status_code == 200, "GET /state → 200", f"got {r.status_code}")
body = r.json()
check("episode_id" in body,        "/state has 'episode_id'")
check("task_id" in body,           "/state has 'task_id'")
check("cumulative_reward" in body, "/state has 'cumulative_reward'")

# ══════════════════════════════════════════════════════════════
section("Phase 2 — Edge cases")
r = requests.post(f"{BASE_URL}/reset", json={"task_id": "task_nonexistent"}, timeout=10)
check(r.status_code == 200, "Invalid task_id → 200 (fallback)", f"got {r.status_code}")

r = requests.post(f"{BASE_URL}/reset", json={}, timeout=10)
check(r.status_code == 200, "Empty reset body → 200", f"got {r.status_code}")

# ══════════════════════════════════════════════════════════════
section("Summary")
if not errors:
    print(f"\n  {PASS} All checks passed — safe to push and resubmit!\n")
else:
    print(f"\n  {FAIL} {len(errors)} check(s) failed:")
    for e in errors:
        print(f"    - {e}")
    print()
    sys.exit(1)
