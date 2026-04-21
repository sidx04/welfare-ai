#!/usr/bin/env python3
"""
demo_what_if_scenarios.py
──────────────────────────

Show counterfactual scenarios for different user profiles across schemes.
Demonstrates the what-if engine with real evaluation data.
"""

import json
from llm.what_if_engine import WhatIfEngine
from scheme_loader import load_scheme
from rule_engine import evaluate_scheme


test_profiles = [
    {
        "name": "High-income farmer",
        "profile": {
            "age": 45,
            "income": 350000,
            "category": "General",
            "state": "Punjab",
            "owns_house": False,
            "owns_lpg": False,
            "land_owned_hectares": 1.5,
            "has_health_insurance": False,
        },
    },
    {
        "name": "Young, no LPG",
        "profile": {
            "age": 28,
            "income": 200000,
            "category": "SC",
            "state": "Bihar",
            "owns_house": False,
            "owns_lpg": False,
            "land_owned_hectares": 0.5,
            "has_health_insurance": False,
        },
    },
    {
        "name": "Elderly, high income",
        "profile": {
            "age": 68,
            "income": 250000,
            "category": "General",
            "state": "Maharashtra",
            "owns_house": True,
            "owns_lpg": True,
            "land_owned_hectares": 2.5,
            "has_health_insurance": False,
        },
    },
]

schemes_to_test = ["pmay", "pmjay", "nsap", "ujjwala", "pmkisan"]

engine = WhatIfEngine()

print("\n" + "=" * 80)
print("  COUNTERFACTUAL SCENARIO DEMO")
print("=" * 80)

for test_case in test_profiles:
    print(f"\n\n📋 Profile: {test_case['name']}")
    print("-" * 80)

    profile = test_case["profile"]

    for scheme_id in schemes_to_test:
        scheme = load_scheme(scheme_id)
        evaluation = evaluate_scheme(profile, scheme)

        if evaluation["eligible"]:
            print(f"\n  ✅ {scheme['scheme_name']}: Already eligible")
            continue

        print(f"\n  ❌ {scheme['scheme_name']}: Not eligible")
        print(f"     Status: {evaluation['status']}")

        scenarios = engine.generate_scenarios(profile, evaluation["trace"])

        if not scenarios:
            print(f"     No improvement paths identified")
            continue

        print(f"     {len(scenarios)} improvement path(s) identified:")

        for i, scenario in enumerate(scenarios[:2], 1):
            feasibility = (
                "🟢"
                if scenario["feasibility_score"] >= 0.7
                else "🟡" if scenario["feasibility_score"] >= 0.4 else "🔴"
            )
            print(f"\n       {i}. {feasibility} {scenario['feasibility_label']}")
            print(f"          Field: {scenario['field']}")
            print(
                f"          Change: {scenario['current_value']} → {scenario['suggested_value']}"
            )
            print(f"          Rationale: {scenario['rationale']}")

print("\n" + "=" * 80)
