"""
Root entrypoint. Uvicorn target: main:app
Run locally:  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import sys
import os

# Ensure root and server/ are both on path
ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(ROOT, "server")
for p in [ROOT, SERVER]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from server.environment import SQLMigrationEnvironment
from models import MigrationAction

app = FastAPI(title="SQL Migration Review Environment")
_env = SQLMigrationEnvironment()


class ResetRequest(BaseModel):
    task_id: str = "task_easy"
    episode_id: Optional[str] = None


class StepRequest(BaseModel):
    checks_requested: List[str]
    severity: str
    recommendation: str
    reasoning: str = ""


def _obs_to_dict(obs, state=None):
    d = {
        "done": obs.done,
        "reward": obs.reward,
        "observation": {
            "task_id": obs.task_id,
            "description": obs.description,
            "migration_sql": obs.migration_sql,
            "table_name": obs.table_name,
            "table_row_count": obs.table_row_count,
            "signals": obs.signals,
            "step": obs.step,
            "max_steps": obs.max_steps,
            "message": obs.message,
        },
    }
    if state:
        d["state"] = {
            "episode_id": state.episode_id,
            "step_count": state.step_count,
            "task_id": state.task_id,
            "cumulative_reward": state.cumulative_reward,
        }
    return d


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/reset")
def reset(req: ResetRequest):
    obs = _env.reset(task_id=req.task_id, episode_id=req.episode_id)
    return _obs_to_dict(obs, _env.state)


@app.post("/step")
def step(req: StepRequest):
    action = MigrationAction(
        checks_requested=req.checks_requested,
        severity=req.severity,
        recommendation=req.recommendation,
        reasoning=req.reasoning,
    )
    obs = _env.step(action)
    return _obs_to_dict(obs, _env.state)


@app.get("/state")
def get_state():
    s = _env.state
    return {
        "episode_id": s.episode_id,
        "step_count": s.step_count,
        "task_id": s.task_id,
        "cumulative_reward": s.cumulative_reward,
    }
