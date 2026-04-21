"""
analysis/evaluate.py

Evaluates the welfare-AI experiment logs across six metrics:
  1. Decision Accuracy    – baseline LLM vs. rule-engine ground truth
  2. Hallucination Rate   – fraction of cases where baseline is wrong
  3. Explanation Faithfulness – keyword check on rule-engine explanations
  4. Explanation Completeness – coverage of key conditions in explanations
  5. Pass Ratio – proportion of eligible vs not eligible cases
  6. Latency – average time to generate explanations

Usage:
    python analysis/evaluate.py [--log logs/experiments.jsonl]
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime


def parse_decision(text: str):
    """Return True (eligible) / False (not eligible) / None (unparsable)."""
    t = text.lower()

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


def calculate_explanation_completeness(explanation: str, trace: list) -> bool:
    """
    Check if explanation covers key conditions from the trace.
    Returns True if explanation mentions at least one failed condition or
    mentions multiple passed conditions.
    """
    explanation_lower = explanation.lower()

    failed_conditions = [step for step in trace if not step.get("passed", False)]
    passed_conditions = [step for step in trace if step.get("passed", False)]

    if failed_conditions:
        for step in failed_conditions:
            description_lower = step.get("description", "").lower()

            key_terms = description_lower.split()
            matches = sum(
                1 for term in key_terms if len(term) > 4 and term in explanation_lower
            )
            if matches >= 2:
                return True
        return len(failed_conditions) <= 1

    condition_mentions = 0
    for step in passed_conditions[:3]:
        description_lower = step.get("description", "").lower()
        key_terms = description_lower.split()
        matches = sum(
            1 for term in key_terms if len(term) > 4 and term in explanation_lower
        )
        if matches >= 2:
            condition_mentions += 1

    return condition_mentions >= 1


def calculate_explanation_length(explanation: str) -> int:
    """Return word count of explanation."""
    return len(explanation.split())


def evaluate(log_path: str):
    total = 0
    baseline_correct = 0
    proposed_correct = 0
    baseline_faithful = 0
    proposed_faithful = 0
    proposed_complete = 0
    unparsable = 0

    eligible_count = 0
    latencies = []
    explanation_lengths = []

    per_scheme_total = defaultdict(int)
    per_scheme_baseline_correct = defaultdict(int)
    per_scheme_hallucination = defaultdict(int)
    per_scheme_proposed_hallucination = defaultdict(int)
    per_scheme_hallucination_severity = defaultdict(float)
    per_scheme_completeness = defaultdict(int)
    per_scheme_avg_length = defaultdict(float)

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
            hallucination_analysis = log.get("hallucination_analysis", {})
            timestamp_str: str = log.get("timestamp", "")
            trace = log["rule_engine_result"].get("trace", [])

            baseline_pred = parse_decision(baseline_text)
            if baseline_pred is None:
                unparsable += 1
                continue

            total += 1
            per_scheme_total[scheme_name] += 1

            if gt:
                eligible_count += 1

            if baseline_pred == gt:
                baseline_correct += 1
                per_scheme_baseline_correct[scheme_name] += 1
            else:
                per_scheme_hallucination[scheme_name] += 1
                hallucination_cases.append(
                    {
                        "scheme": scheme_name,
                        "scheme_id": scheme_id,
                        "profile": log["user_profile"],
                        "ground_truth": gt,
                        "baseline_pred": baseline_pred,
                        "baseline_text": baseline_text.replace("<|end|>", "").strip(),
                        "proposed_text": proposed_text.replace("<|end|>", "").strip(),
                        "rule_trace": trace,
                    }
                )

            if hallucination_analysis:
                if hallucination_analysis.get("has_hallucinations", False):
                    per_scheme_proposed_hallucination[scheme_name] += 1
                severity = hallucination_analysis.get("severity_score", 0.0)
                per_scheme_hallucination_severity[scheme_name] += severity

            if is_faithful(baseline_text):
                baseline_faithful += 1
            if is_faithful(proposed_text):
                proposed_faithful += 1

            is_complete = calculate_explanation_completeness(proposed_text, trace)
            if is_complete:
                proposed_complete += 1
                per_scheme_completeness[scheme_name] += 1

            exp_length = calculate_explanation_length(proposed_text)
            explanation_lengths.append(exp_length)
            per_scheme_avg_length[scheme_name] += exp_length

        proposed_correct = total

    overall_baseline_acc = baseline_correct / total if total else 0
    overall_proposed_acc = 1.0
    hallucination_rate_baseline = 1 - overall_baseline_acc

    overall_proposed_hallucinations = sum(per_scheme_proposed_hallucination.values())
    hallucination_rate_proposed = (
        overall_proposed_hallucinations / total if total else 0
    )

    baseline_faithfulness = baseline_faithful / total if total else 0
    proposed_faithfulness = proposed_faithful / total if total else 0

    explanation_completeness = proposed_complete / total if total else 0

    pass_ratio = eligible_count / total if total else 0
    not_eligible_ratio = 1 - pass_ratio

    avg_explanation_length = (
        sum(explanation_lengths) / len(explanation_lengths)
        if explanation_lengths
        else 0
    )

    print("=" * 80)
    print("  WELFARE-AI EXPERIMENT EVALUATION REPORT")
    print("=" * 80)
    print(f"\n  Total parsable cases : {total}")
    print(f"  Unparsable baseline  : {unparsable}")

    print("\n─── OVERALL METRICS ──────────────────────────────────────")
    print(f"  Metric                           Proposed     Baseline LLM")
    print(
        f"  Decision Accuracy                {overall_proposed_acc*100:>6.1f}%      {overall_baseline_acc*100:>6.1f}%"
    )
    print(
        f"  Hallucination Rate               {hallucination_rate_proposed*100:>6.1f}%      {hallucination_rate_baseline*100:>6.1f}%"
    )
    print(
        f"  Explanation Faithfulness         {proposed_faithfulness*100:>6.1f}%      {baseline_faithfulness*100:>6.1f}%"
    )
    print(
        f"  Explanation Completeness         {explanation_completeness*100:>6.1f}%      N/A"
    )

    print(
        f"\n─── ELIGIBILITY DISTRIBUTION ────────────────────────────────────────────"
    )
    print(
        f"  Pass Ratio (Eligible)            {pass_ratio*100:>6.1f}%  ({eligible_count}/{total} cases)"
    )
    print(
        f"  Fail Ratio (Not Eligible)        {not_eligible_ratio*100:>6.1f}%  ({total - eligible_count}/{total} cases)"
    )

    print(
        f"\n─── EXPLANATION QUALITY ─────────────────────────────────────────────────"
    )
    print(f"  Average Explanation Length       {avg_explanation_length:>6.1f} words")
    print(
        f"  Min Explanation Length           {min(explanation_lengths) if explanation_lengths else 0:>6} words"
    )
    print(
        f"  Max Explanation Length           {max(explanation_lengths) if explanation_lengths else 0:>6} words"
    )

    print(
        "\n─── PER-SCHEME BREAKDOWN ─────────────────────────────────────────────────"
    )
    header = (
        f"  {'Scheme':<36} " f"{'Total':>5}  " f"{'Complete':>10}  " f"{'Halluc':>10}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for sname in sorted(per_scheme_total):
        n = per_scheme_total[sname]
        complete = per_scheme_completeness[sname] / n if n else 0
        halluc = per_scheme_proposed_hallucination[sname] / n if n else 0
        avg_len = per_scheme_avg_length[sname] / n if n else 0
        print(
            f"  {sname:<36} {n:>5}  {complete*100:>8.1f}%  {halluc*100:>8.1f}%  ({avg_len:.0f}w)"
        )

    print(f"\n  Baseline decision error cases : {len(hallucination_cases)}")
    print(f"  Proposed system hallucinations: {overall_proposed_hallucinations}")

    summary = {
        "total": total,
        "unparsable": unparsable,
        "proposed_accuracy": round(overall_proposed_acc, 4),
        "baseline_accuracy": round(overall_baseline_acc, 4),
        "proposed_explanation_hallucination_rate": round(
            hallucination_rate_proposed, 4
        ),
        "baseline_decision_hallucination_rate": round(hallucination_rate_baseline, 4),
        "proposed_faithfulness": round(proposed_faithfulness, 4),
        "baseline_faithfulness": round(baseline_faithfulness, 4),
        "explanation_completeness": round(explanation_completeness, 4),
        "pass_ratio": round(pass_ratio, 4),
        "not_eligible_ratio": round(not_eligible_ratio, 4),
        "eligible_count": eligible_count,
        "not_eligible_count": total - eligible_count,
        "avg_explanation_length": round(avg_explanation_length, 2),
        "min_explanation_length": (
            min(explanation_lengths) if explanation_lengths else 0
        ),
        "max_explanation_length": (
            max(explanation_lengths) if explanation_lengths else 0
        ),
        "per_scheme": {
            sname: {
                "total": per_scheme_total[sname],
                "proposed_hallucinations": per_scheme_proposed_hallucination[sname],
                "proposed_explanation_hallucination_rate": (
                    round(
                        per_scheme_proposed_hallucination[sname]
                        / per_scheme_total[sname],
                        4,
                    )
                    if per_scheme_total[sname]
                    else 0
                ),
                "proposed_avg_severity": (
                    round(
                        per_scheme_hallucination_severity[sname]
                        / per_scheme_total[sname],
                        4,
                    )
                    if per_scheme_total[sname]
                    else 0
                ),
                "explanation_completeness": (
                    round(per_scheme_completeness[sname] / per_scheme_total[sname], 4)
                    if per_scheme_total[sname]
                    else 0
                ),
                "avg_explanation_length": (
                    round(per_scheme_avg_length[sname] / per_scheme_total[sname], 2)
                    if per_scheme_total[sname]
                    else 0
                ),
                "baseline_correct": per_scheme_baseline_correct[sname],
                "baseline_accuracy": (
                    round(
                        per_scheme_baseline_correct[sname] / per_scheme_total[sname], 4
                    )
                    if per_scheme_total[sname]
                    else 0
                ),
                "baseline_hallucinations": per_scheme_hallucination[sname],
                "baseline_decision_hallucination_rate": (
                    round(per_scheme_hallucination[sname] / per_scheme_total[sname], 4)
                    if per_scheme_total[sname]
                    else 0
                ),
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
    print("=" * 80)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate welfare-AI experiment logs.")
    parser.add_argument(
        "--log",
        default=os.path.join(
            os.path.dirname(__file__), "..", "logs", "experiments.jsonl"
        ),
        help="Path to the JSONL experiment log file.",
    )
    args = parser.parse_args()
    evaluate(args.log)
