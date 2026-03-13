"""
run_experiments.py
------------------
Exhaustive experiment runner: sweeps 8 user profiles x 5 schemes (40 total)
and appends each result to logs/experiments.jsonl via the existing logger.

Run:
    source venv/bin/activate
    python run_experiments.py
"""

import time

from scheme_loader import load_scheme
from rule_engine import evaluate_scheme
from llm.phi3 import Phi3LLM
from llm.prompts import build_explanation_prompt, format_explanation_block
from baseline.run_baseline import run_baseline
from experiment_logging.experiment_logger import log_experiment

# ─────────────────────────────────────────────
# 1. All scheme IDs
# ─────────────────────────────────────────────

SCHEME_IDS = ["pmay", "pmjay", "nsap", "ujjwala", "pmkisan"]

# ─────────────────────────────────────────────
# 2. Test profiles — engineered to hit distinct
#    pass/fail combos across all five schemes
# ─────────────────────────────────────────────

TEST_PROFILES = [
    {
        "_label": "low_income_sc_rural",
        # Designed to pass most schemes
        "age": 35,
        "income": 150000,
        "category": "SC",
        "state": "Rajasthan",
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": 1.0,
        "has_health_insurance": False,
    },
    {
        "_label": "high_income_general",
        # Fails income-based schemes (pmay, nsap, pmkisan)
        "age": 42,
        "income": 900000,
        "category": "General",
        "state": "Maharashtra",
        "owns_house": True,
        "owns_lpg": True,
        "land_owned_hectares": 5.0,
        "has_health_insurance": True,
    },
    {
        "_label": "elderly_bpl",
        # Targets NSAP: age >= 60, income <= 2L
        "age": 68,
        "income": 120000,
        "category": "BPL",
        "state": "Bihar",
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": 0.5,
        "has_health_insurance": False,
    },
    {
        "_label": "young_small_farmer",
        # Targets PM-KISAN: land <= 2ha, low income
        "age": 26,
        "income": 180000,
        "category": "OBC",
        "state": "Punjab",
        "owns_house": False,
        "owns_lpg": True,
        "land_owned_hectares": 1.8,
        "has_health_insurance": False,
    },
    {
        "_label": "boundary_income_ews",
        # Income exactly at PMAY EWS limit — edge case
        "age": 30,
        "income": 300000,
        "category": "SC",
        "state": "UP",
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": 0.8,
        "has_health_insurance": False,
    },
    {
        "_label": "st_no_lpg",
        # Targets Ujjwala: ST category, no LPG
        "age": 29,
        "income": 220000,
        "category": "ST",
        "state": "Jharkhand",
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": 1.2,
        "has_health_insurance": False,
    },
    {
        "_label": "owns_house_sc",
        # Fails PMAY (owns house), eligible for others where applicable
        "age": 40,
        "income": 200000,
        "category": "SC",
        "state": "TN",
        "owns_house": True,
        "owns_lpg": False,
        "land_owned_hectares": 1.5,
        "has_health_insurance": False,
    },
    {
        "_label": "minor_profile",
        # Fails age-gated schemes (pmay, nsap)
        "age": 16,
        "income": 100000,
        "category": "SC",
        "state": "Kerala",
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": 0.3,
        "has_health_insurance": False,
    },
]

MODEL_METADATA = {
    "model": "phi-3-mini-4k-instruct-4bit",
    "temperature": 0,
    "max_tokens": 80,
}

# ─────────────────────────────────────────────
# 3. Pre-strip internal _label keys once
# ─────────────────────────────────────────────

PROFILES = [
    (p["_label"], {k: v for k, v in p.items() if not k.startswith("_")})
    for p in TEST_PROFILES
]

# ─────────────────────────────────────────────
# 4. Load model once — expensive, do it once
# ─────────────────────────────────────────────

print("Loading Phi-3 Mini Instruct (once for all experiments)...")
llm = Phi3LLM()

# ─────────────────────────────────────────────
# 5. Sweep
# ─────────────────────────────────────────────

total = len(PROFILES) * len(SCHEME_IDS)
counter = 0
overall_start = time.perf_counter()

print(f"Starting sweep: {len(SCHEME_IDS)} schemes x {len(PROFILES)} profiles = {total} experiments\n")

for scheme_id in SCHEME_IDS:
    scheme = load_scheme(scheme_id)
    scheme_start = time.perf_counter()

    for label, user_profile in PROFILES:
        counter += 1

        # --- Rule engine (deterministic) ---
        evaluation = evaluate_scheme(user_profile, scheme)
        structured_block = format_explanation_block(scheme["scheme_name"], evaluation)

        # --- Proposed system explanation ---
        prompt = build_explanation_prompt(scheme["scheme_name"], evaluation)
        full_explanation = llm.generate(prompt, max_tokens=80).strip()

        # --- Baseline LLM ---
        baseline_output = run_baseline(llm, scheme_id, scheme["scheme_name"], user_profile)

        # --- Progress ---
        eligible_str = "eligible" if evaluation["eligible"] else "NOT eligible"
        print(f"  [{counter:>2}/{total}] {scheme_id} x {label:<25} -> {eligible_str}")

        # --- Log (silent: no per-record print inside the sweep) ---
        log_experiment(
            scheme_id=scheme_id,
            scheme_name=scheme["scheme_name"],
            user_profile=user_profile,
            rule_engine_result=evaluation,
            proposed_system_explanation=full_explanation,
            baseline_llm_output=baseline_output.strip(),
            model_metadata=MODEL_METADATA,
            verbose=False,
        )

    scheme_elapsed = time.perf_counter() - scheme_start
    print(f"  => {scheme_id} done in {scheme_elapsed:.1f}s\n")

overall_elapsed = time.perf_counter() - overall_start
print(f"Done. {total} experiments logged -> logs/experiments.jsonl  ({overall_elapsed:.1f}s total)")
