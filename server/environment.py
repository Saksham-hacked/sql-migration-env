import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from models import MigrationAction, MigrationObservation, MigrationState
from tasks import TASKS, grade

MAX_STEPS = 1  # One-shot per episode (agent gets full context, makes one decision)


class SQLMigrationEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._state = MigrationState()
        self._task = None
        self._done = False

    def reset(self, task_id: str = "task_easy", episode_id: str = None, **kwargs) -> MigrationObservation:
        if task_id not in TASKS:
            task_id = "task_easy"
        self._task = TASKS[task_id]
        self._done = False
        self._state = MigrationState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_id=task_id,
            cumulative_reward=0.0,
        )
        return self._make_obs(reward=None, message="Review this migration and submit your triage decision.")

    def step(self, action: MigrationAction, **kwargs) -> MigrationObservation:
        if self._task is None:
            # reset() was never called — auto-initialize with default task
            self.reset(task_id="task_easy")
        if self._done:
            return self._make_obs(reward=0.0001, message="Episode already complete. Call reset().")

        self._state.step_count += 1
        raw_score = grade(self._task["id"], action)
        # Clamp strictly to open interval (0, 1) — validator requires 0 < score < 1
        score = max(0.0001, min(raw_score, 0.9999))
        # Never allow exact 0.0 or 1.0
        if score <= 0.0:
            score = 0.0001
        if score >= 1.0:
            score = 0.9999
        self._state.cumulative_reward += score
        self._done = True

        if score >= 0.85:
            msg = f"Excellent triage. Score: {score:.2f}"
        elif score >= 0.55:
            msg = f"Partial credit. Score: {score:.2f}. Some checks or classification missed."
        else:
            msg = f"Poor triage. Score: {score:.2f}. Review severity/recommendation/checks."

        return self._make_obs(reward=score, message=msg)

    @property
    def state(self) -> MigrationState:
        return self._state

    def _make_obs(self, reward, message) -> MigrationObservation:
        t = self._task
        return MigrationObservation(
            done=self._done,
            reward=reward,
            task_id=t["id"],
            description=t["description"],
            migration_sql=t["migration_sql"],
            table_name=t["table_name"],
            table_row_count=t["table_row_count"],
            signals=t["signals"],
            step=self._state.step_count,
            max_steps=MAX_STEPS,
            message=message,
        )
