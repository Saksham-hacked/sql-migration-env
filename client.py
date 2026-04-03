from typing import Optional

import requests

from models import StepRequest, StepResult


class SQLMigrationEnvClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def reset(self, task_id: Optional[str] = None) -> StepResult:
        payload = {}
        if task_id:
            payload["task_id"] = task_id

        response = requests.post(f"{self.base_url}/reset", json=payload, timeout=30)
        response.raise_for_status()
        return StepResult(**response.json())

    def step(self, action: StepRequest) -> StepResult:
        response = requests.post(
            f"{self.base_url}/step",
            json=action.model_dump(),
            timeout=30,
        )
        response.raise_for_status()
        return StepResult(**response.json())

    def state(self):
        response = requests.get(f"{self.base_url}/state", timeout=30)
        response.raise_for_status()
        return response.json()