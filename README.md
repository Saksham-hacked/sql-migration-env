---
title: SQL Migration Env
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: OpenEnv environment for evaluating SQL migration safety
---


# SQL Migration Review Environment

An OpenEnv environment where an AI agent acts as a database migration triage engineer. Given a SQL migration script and context signals, the agent must classify severity, recommend action, and select the appropriate safety checks.
## Motivation

Every engineering team shipping database migrations faces the same risk: a bad `ALTER TABLE` or `CREATE INDEX` on a large production table can take down a service. This environment trains and evaluates agents on exactly that judgment call.

## Environment Interface

| Method | Description |
|--------|-------------|
| `POST /reset` | Start a new episode with a specific task |
| `POST /step` | Submit a triage decision |
| `GET /state` | Get episode metadata |
| `GET /health` | Health check |

## Action Space

```json
{
  "checks_requested": ["check_rollback", "check_nullability", "check_index_safety", "check_destructive", "check_lock_risk"],
  "severity": "safe | low | medium | high | critical",
  "recommendation": "approve | request_changes | escalate | block",
  "reasoning": "optional string"
}
```

## Observation Space

```json
{
  "task_id": "task_easy | task_medium | task_hard",
  "description": "natural language description of the migration",
  "migration_sql": "the SQL statement",
  "table_name": "string",
  "table_row_count": 85000,
  "signals": {
    "has_rollback": false,
    "is_destructive": true,
    "nullable_violation": false,
    "index_type": null,
    "uses_lock": false,
    "is_production_critical": false
  },
  "step": 1,
  "max_steps": 1,
  "message": "feedback string"
}
```

## Tasks

| Task | Difficulty | Scenario | Ground Truth |
|------|-----------|----------|--------------|
| `task_easy` | Easy | DROP COLUMN without rollback on 1,200-row table | severity=high, rec=request_changes |
| `task_medium` | Medium | NOT NULL column without DEFAULT on 85,000-row production table | severity=critical, rec=block |
| `task_hard` | Hard | Blocking index build (no CONCURRENTLY) on 4.2M-row payments table | severity=critical, rec=escalate |

## Scoring

Each task is graded 0.0–1.0 across three dimensions:
- **Severity classification** (30%) — exact match full credit, adjacent level gets 50%
- **Recommendation** (35%) — exact match required; adjacent recommendation gets 40%
- **Checks overlap** (35%) — Jaccard similarity with required checks set

## Setup

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860
```

## Docker

```bash
docker build -t sql-migration-env .
docker run -p 7860:7860 sql-migration-env
```

## Baseline Inference

```bash
export ENV_URL=http://localhost:7860
export API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
export MODEL_NAME=gemini-2.5-flash
export HF_TOKEN=your_key_here
python inference.py
```

### Stdout format

The script emits mandatory structured lines:

```
[START] task=task_easy env=sql-migration-env model=gemini-2.5-flash
[STEP] step=1 action=severity=high,rec=request_changes,checks=[check_rollback|check_destructive] reward=1.00 done=true error=null
[END] success=true steps=1 rewards=1.00
```

## Baseline Scores (gemini-2.5-flash, temperature=0)

| Task | Score |
|------|-------|
| task_easy | 1.00 |
| task_medium | 1.00 |
| task_hard | 1.00 |
| **Average** | **1.00** |
