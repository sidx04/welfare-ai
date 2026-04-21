#!/usr/bin/env python3
"""
Quick test script to validate hallucination detection on existing JSONL data.
"""

import json
import sys
from llm.hallucination_detector import HallucinationDetector


detector = HallucinationDetector()

test_cases = []
with open("logs/experiments.jsonl", "r") as f:
    for i, line in enumerate(f):

        log = json.loads(line)
        explanation = log.get("proposed_system_explanation", "").strip()
        trace = log.get("rule_engine_result", {}).get("trace", [])
        scheme_name = log.get("scheme_name", "unknown")

        result = detector.detect_hallucinations(explanation, trace)
        test_cases.append(
            {
                "scheme": scheme_name,
                "explanation": explanation[:80] + "...",
                "has_hallucinations": result["has_hallucinations"],
                "count": result["hallucination_count"],
                "severity": result["severity_score"],
                "hallucinations": result["hallucinations"],
            }
        )


print("\n" + "=" * 80)
print("  HALLUCINATION DETECTION TEST (First 10 records)")
print("=" * 80 + "\n")

for i, case in enumerate(test_cases, 1):
    halluc_str = (
        "✓ OK"
        if not case["has_hallucinations"]
        else f"⚠ {case['count']} hallucinations"
    )
    print(f"{i}. {case['scheme']:<40} {halluc_str}")
    print(f"   Severity: {case['severity']:.2f}")
    if case["hallucinations"]:
        for h in case["hallucinations"]:
            print(f"     - {h['type']}: {h['description']}")
    print()

print("=" * 80)
