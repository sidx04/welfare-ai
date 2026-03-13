"""
analysis/evaluate.py

Evaluates the welfare-AI experiment logs across three metrics:
  1. Decision Accuracy    – baseline LLM vs. rule-engine ground truth
  2. Hallucination Rate   – fraction of cases where baseline is wrong
  3. Explanation Faithfulness – keyword check on rule-engine explanations
                              vs. baseline LLM explanations

Usage:
    python analysis/evaluate.py [--log logs/experiments.jsonl]
"""

import argparse
import json
import os
from collections import defaultdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_decision(text: str):
    """Return True (eligible) / False (not eligible) / None (unparsable)."""
    t = text.lower()
    # "not eligible" must be checked before "eligible"
    if "not eligible" in t:
        return False
    if "eligible" in t:
        return True
    return None


FAITHFULNESS_KEYWORDS = [
    "income",
    "ews",
    "pucca house",
    "owns house",
    "age",
    "lpg",
    "land",
    "hectare",
    "category",
    "sc",
    "st",
    "bpl",
    "health insurance",
    "poverty",
    "exclusion threshold",
    "small landholding",
]


def is_faithful(explanation: str) -> bool:
    """Check whether the explanation references actual rule-based conditions."""
    text = explanation.lower()
    return any(kw in text for kw in FAITHFULNESS_KEYWORDS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def evaluate(log_path: str):
    total = 0
    baseline_correct = 0
    proposed_correct = 0   # proposed == rule engine by definition; tracked for sanity
    baseline_faithful = 0
    proposed_faithful = 0
    unparsable = 0

    per_scheme_total = defaultdict(int)
    per_scheme_baseline_correct = defaultdict(int)
    per_scheme_hallucination = defaultdict(int)

    hallucination_cases = []

    with open(log_path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            log = json.loads(raw)

            gt: bool = log["rule_engine_result"]["eligible"]
            scheme_id: str = log["scheme_id"]
            scheme_name: str = log["scheme_name"]
            baseline_text: str = log.get("baseline_llm_output", "")
            proposed_text: str = log.get("proposed_system_explanation", "")

            baseline_pred = parse_decision(baseline_text)
            if baseline_pred is None:
                unparsable += 1
                continue

            total += 1
            per_scheme_total[scheme_name] += 1

            # --- Accuracy ---
            if baseline_pred == gt:
                baseline_correct += 1
                per_scheme_baseline_correct[scheme_name] += 1
            else:
                # Hallucination: LLM sided wrong
                per_scheme_hallucination[scheme_name] += 1
                hallucination_cases.append({
                    "scheme": scheme_name,
                    "scheme_id": scheme_id,
                    "profile": log["user_profile"],
                    "ground_truth": gt,
                    "baseline_pred": baseline_pred,
                    "baseline_text": baseline_text.replace("<|end|>", "").strip(),
                    "proposed_text": proposed_text.replace("<|end|>", "").strip(),
                    "rule_trace": log["rule_engine_result"].get("trace", []),
                })

            # --- Faithfulness ---
            if is_faithful(baseline_text):
                baseline_faithful += 1
            if is_faithful(proposed_text):
                proposed_faithful += 1

        # Proposed system is deterministic (rule engine result), so it's always 100%
        proposed_correct = total  # rule engine IS the ground truth

    # ---------------------------------------------------------------------------
    # Results
    # ---------------------------------------------------------------------------
    overall_baseline_acc = baseline_correct / total if total else 0
    overall_proposed_acc = 1.0  # rule engine is ground truth
    hallucination_rate_baseline = 1 - overall_baseline_acc
    hallucination_rate_proposed = 0.0

    baseline_faithfulness = baseline_faithful / total if total else 0
    proposed_faithfulness = proposed_faithful / total if total else 0

    print("=" * 62)
    print("  WELFARE-AI EXPERIMENT EVALUATION REPORT")
    print("=" * 62)
    print(f"\n  Total parsable cases : {total}")
    print(f"  Unparsable baseline  : {unparsable}")

    print("\n─── OVERALL METRICS ──────────────────────────────────────")
    print(f"  Metric                    Proposed     Baseline LLM")
    print(f"  Decision Accuracy         {overall_proposed_acc*100:>6.1f}%      {overall_baseline_acc*100:>6.1f}%")
    print(f"  Hallucination Rate        {hallucination_rate_proposed*100:>6.1f}%      {hallucination_rate_baseline*100:>6.1f}%")
    print(f"  Explanation Faithfulness  {proposed_faithfulness*100:>6.1f}%      {baseline_faithfulness*100:>6.1f}%")

    print("\n─── PER-SCHEME BREAKDOWN ─────────────────────────────────")
    header = f"  {'Scheme':<45} {'Total':>5}  {'Baseline Acc':>12}  {'Hallucinations':>14}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for sname in sorted(per_scheme_total):
        n = per_scheme_total[sname]
        b_acc = per_scheme_baseline_correct[sname] / n if n else 0
        h = per_scheme_hallucination[sname]
        print(f"  {sname:<45} {n:>5}  {b_acc*100:>11.1f}%  {h:>14}")

    print(f"\n  Total hallucination cases : {len(hallucination_cases)}")

    # Save summary JSON
    summary = {
        "total": total,
        "unparsable": unparsable,
        "proposed_accuracy": round(overall_proposed_acc, 4),
        "baseline_accuracy": round(overall_baseline_acc, 4),
        "baseline_hallucination_rate": round(hallucination_rate_baseline, 4),
        "proposed_hallucination_rate": round(hallucination_rate_proposed, 4),
        "proposed_faithfulness": round(proposed_faithfulness, 4),
        "baseline_faithfulness": round(baseline_faithfulness, 4),
        "per_scheme": {
            sname: {
                "total": per_scheme_total[sname],
                "baseline_correct": per_scheme_baseline_correct[sname],
                "hallucinations": per_scheme_hallucination[sname],
                "baseline_accuracy": round(
                    per_scheme_baseline_correct[sname] / per_scheme_total[sname], 4
                ) if per_scheme_total[sname] else 0,
            }
            for sname in per_scheme_total
        },
        "hallucination_cases": hallucination_cases,
    }

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print(f"\n  Full results saved → {out_path}")
    print("=" * 62)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate welfare-AI experiment logs.")
    parser.add_argument(
        "--log",
        default=os.path.join(os.path.dirname(__file__), "..", "logs", "experiments.jsonl"),
        help="Path to the JSONL experiment log file.",
    )
    args = parser.parse_args()
    evaluate(args.log)
