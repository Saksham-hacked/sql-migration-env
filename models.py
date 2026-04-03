from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class MigrationAction:
    """Agent's triage decision for a SQL migration."""
    checks_requested: List[str]   # subset of: check_rollback, check_nullability, check_index_safety, check_destructive, check_lock_risk
    severity: str                  # safe | low | medium | high | critical
    recommendation: str            # approve | request_changes | escalate | block
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationObservation:
    """What the agent sees at each step."""
    done: bool
    reward: Optional[float]
    task_id: str
    description: str
    migration_sql: str
    table_name: str
    table_row_count: int           # estimated rows affected
    signals: Dict[str, Any]        # flags: has_rollback, nullable_violations, index_type, etc.
    step: int
    max_steps: int
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationState:
    """Episode metadata."""
    episode_id: Optional[str] = None
    step_count: int = 0
    task_id: str = ""
    cumulative_reward: float = 0.0
