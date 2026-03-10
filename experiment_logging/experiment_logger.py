import json
import os
from datetime import datetime, timezone


LOGS_DIR = "logs"
EXPERIMENTS_LOG = os.path.join(LOGS_DIR, "experiments.jsonl")


def log_experiment(
    scheme_id: str,
    scheme_name: str,
    user_profile: dict,
    rule_engine_result: dict,
    proposed_system_explanation: str,
    baseline_llm_output: str,
    model_metadata: dict,
) -> None:
    """
    Append a single experiment record to logs/experiments.jsonl.

    Creates the logs/ directory if it does not already exist.
    Each record is written as one JSON line (JSONL format) so the
    file remains streamable and pandas-compatible.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "user_profile": user_profile,
        "rule_engine_result": rule_engine_result,
        "proposed_system_explanation": proposed_system_explanation,
        "baseline_llm_output": baseline_llm_output,
        "model_metadata": model_metadata,
    }

    with open(EXPERIMENTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[logger] Experiment record appended → {EXPERIMENTS_LOG}")
