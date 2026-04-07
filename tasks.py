"""
Task definitions for SQL Migration Review environment.
Each task has: migration SQL, signals, ground truth, and a deterministic grader.
"""

TASKS = {
    "task_easy": {
        "id": "task_easy",
        "description": (
            "A developer added a DROP COLUMN statement to remove the deprecated `legacy_notes` "
            "column from the `users` table. No rollback script was included. The table has 1,200 rows."
        ),
        "migration_sql": (
            "ALTER TABLE users DROP COLUMN legacy_notes;"
        ),
        "table_name": "users",
        "table_row_count": 1200,
        "signals": {
            "has_rollback": False,
            "is_destructive": True,
            "nullable_violation": False,
            "index_type": None,
            "uses_lock": False,
            "is_production_critical": False,
        },
        "ground_truth": {
            "severity": "high",
            "recommendation": "request_changes",
            "required_checks": {"check_rollback", "check_destructive"},
        },
        "weights": {
            "severity": 0.30,
            "recommendation": 0.35,
            "checks": 0.35,
        },
    },

    "task_medium": {
        "id": "task_medium",
        "description": (
            "A developer added a NOT NULL column `subscription_tier` to the `accounts` table "
            "without a DEFAULT value. The table has 85,000 rows in production. "
            "No rollback script included."
        ),
        "migration_sql": (
            "ALTER TABLE accounts ADD COLUMN subscription_tier VARCHAR(32) NOT NULL;"
        ),
        "table_name": "accounts",
        "table_row_count": 85000,
        "signals": {
            "has_rollback": False,
            "is_destructive": False,
            "nullable_violation": True,       # NOT NULL without DEFAULT on existing rows
            "index_type": None,
            "uses_lock": True,                # ALTER TABLE locks in most DBs
            "is_production_critical": True,
        },
        "ground_truth": {
            "severity": "critical",
            "recommendation": "block",
            "required_checks": {"check_nullability", "check_rollback", "check_lock_risk"},
        },
        "weights": {
            "severity": 0.30,
            "recommendation": 0.35,
            "checks": 0.35,
        },
    },

    "task_hard": {
        "id": "task_hard",
        "description": (
            "A developer is adding a B-TREE index on `payments.created_at` using a standard "
            "CREATE INDEX (not CONCURRENTLY). The payments table has 4.2 million rows and is "
            "written to continuously. No rollback script. Deployed during business hours."
        ),
        "migration_sql": (
            "CREATE INDEX idx_payments_created_at ON payments (created_at);"
        ),
        "table_name": "payments",
        "table_row_count": 4200000,
        "signals": {
            "has_rollback": False,
            "is_destructive": False,
            "nullable_violation": False,
            "index_type": "btree_blocking",   # blocking = without CONCURRENTLY
            "uses_lock": True,                # table-level lock during index build
            "is_production_critical": True,
        },
        "ground_truth": {
            "severity": "critical",
            "recommendation": "escalate",
            "required_checks": {"check_lock_risk", "check_index_safety", "check_rollback"},
        },
        "weights": {
            "severity": 0.30,
            "recommendation": 0.35,
            "checks": 0.35,
        },
    },
}


VALID_CHECKS = {
    "check_rollback",
    "check_nullability",
    "check_index_safety",
    "check_destructive",
    "check_lock_risk",
}

SEVERITY_LEVELS = ["safe", "low", "medium", "high", "critical"]

RECOMMENDATIONS = ["approve", "request_changes", "escalate", "block"]


def grade(task_id: str, action) -> float:
    """
    Deterministic grader. Returns score in [0.0, 1.0].
    Partial credit on each dimension.
    """
    task = TASKS[task_id]
    gt = task["ground_truth"]
    w = task["weights"]
    score = 0.0

    # 1. Severity score (exact match full credit, adjacent partial)
    sev_idx = SEVERITY_LEVELS.index(action.severity) if action.severity in SEVERITY_LEVELS else -1
    gt_sev_idx = SEVERITY_LEVELS.index(gt["severity"])
    if sev_idx == gt_sev_idx:
        score += w["severity"]
    elif abs(sev_idx - gt_sev_idx) == 1:
        score += w["severity"] * 0.5

    # 2. Recommendation score (exact match)
    if action.recommendation == gt["recommendation"]:
        score += w["recommendation"]
    elif _is_adjacent_recommendation(action.recommendation, gt["recommendation"]):
        score += w["recommendation"] * 0.4

    # 3. Checks overlap score (Jaccard similarity)
    requested = set(c for c in action.checks_requested if c in VALID_CHECKS)
    required = gt["required_checks"]
    if required:
        jaccard = len(requested & required) / len(requested | required) if (requested | required) else 0.0
        score += w["checks"] * jaccard

    # Clamp strictly to open interval (0, 1) — validator requires 0 < score < 1
    score = max(0.0001, min(score, 0.9999))
    return round(score, 4)


def _is_adjacent_recommendation(pred: str, gt: str) -> bool:
    order = ["approve", "request_changes", "escalate", "block"]
    if pred not in order or gt not in order:
        return False
    return abs(order.index(pred) - order.index(gt)) == 1
