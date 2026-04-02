"""
run_synthetic_experiments.py
-----------------------------
Generates N=100 synthetic user profiles via stratified random sampling,
then runs 5 schemes × 100 profiles = 500 experiments, appending every
result to logs/experiments.jsonl via the standard experiment logger.

Strategy
--------
Profiles are generated to give good coverage of boundary conditions:
  - 40% drawn from a fully random distribution
  - 60% drawn from "targeted" strata that deliberately exercise 
    eligibility boundaries for each scheme
This ensures the log captures diverse pass/fail distributions and is
not dominated by trivially easy cases.

Run:
    source venv/bin/activate
    python run_synthetic_experiments.py
"""

import random
import time
from typing import List, Dict, Any

from scheme_loader import load_scheme
from rule_engine import evaluate_scheme
from llm.phi3 import Phi3LLM
from llm.prompts import build_explanation_prompt, format_explanation_block
from baseline.run_baseline import run_baseline
from experiment_logging.experiment_logger import log_experiment

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

SEED = 42
N_PROFILES = 100
SCHEME_IDS = ["pmay", "pmjay", "nsap", "ujjwala", "pmkisan"]

MODEL_METADATA = {
    "model": "phi-3-mini-4k-instruct-4bit",
    "temperature": 0,
    "max_tokens": 256,
}

# ─────────────────────────────────────────────────────────────
# Field value pools (mirrors real Indian demographic variety)
# ─────────────────────────────────────────────────────────────

CATEGORIES = ["SC", "ST", "OBC", "BPL", "General"]
STATES = [
    "Rajasthan", "UP", "Bihar", "Maharashtra", "Karnataka",
    "TN", "Kerala", "Punjab", "Jharkhand", "MP",
    "Gujarat", "West Bengal", "Odisha", "Assam", "Haryana",
]

# Income brackets (annual, INR) — with weights to favour lower-income
INCOME_RANGES = [
    (50_000,  100_000),   # very poor
    (100_001, 200_000),   # low income
    (200_001, 300_000),   # EWS boundary zone
    (300_001, 500_000),   # above EWS
    (500_001, 1_000_000), # high income
    (1_000_001, 2_000_000), # very high
]
INCOME_WEIGHTS = [0.18, 0.22, 0.20, 0.15, 0.15, 0.10]

# Land (hectares) — range chosen to straddle PM-KISAN's 2 ha limit
LAND_RANGES = [
    (0.0,  0.5),
    (0.5,  1.0),
    (1.0,  2.0),
    (2.0,  3.5),
    (3.5, 10.0),
]
LAND_WEIGHTS = [0.20, 0.25, 0.25, 0.15, 0.15]


# ─────────────────────────────────────────────────────────────
# Utility samplers
# ─────────────────────────────────────────────────────────────

def weighted_choice(rng: random.Random, ranges, weights):
    lo, hi = rng.choices(ranges, weights=weights, k=1)[0]
    return round(rng.uniform(lo, hi), 2)


def random_profile(rng: random.Random) -> Dict[str, Any]:
    """Fully random profile — no special targeting."""
    income = int(weighted_choice(rng, INCOME_RANGES, INCOME_WEIGHTS))
    return {
        "age": rng.randint(14, 80),
        "income": income,
        "category": rng.choice(CATEGORIES),
        "state": rng.choice(STATES),
        "owns_house": rng.random() < 0.35,
        "owns_lpg": rng.random() < 0.40,
        "land_owned_hectares": round(weighted_choice(rng, LAND_RANGES, LAND_WEIGHTS), 2),
        "has_health_insurance": rng.random() < 0.15,
    }


# ─────────────────────────────────────────────────────────────
# Strata generators — each targets a specific boundary
# ─────────────────────────────────────────────────────────────

def stratum_pmay_boundary(rng: random.Random) -> Dict[str, Any]:
    """Income near the ₹3L EWS limit; age near 18."""
    income = rng.choice([
        rng.randint(250_000, 299_999),   # just under
        300_000,                         # exactly at limit
        rng.randint(300_001, 350_000),   # just over
    ])
    return {
        "age": rng.choice([rng.randint(16, 19), rng.randint(20, 60)]),
        "income": income,
        "category": rng.choice(["SC", "ST", "OBC", "General"]),
        "state": rng.choice(STATES),
        "owns_house": rng.random() < 0.5,
        "owns_lpg": rng.random() < 0.5,
        "land_owned_hectares": round(rng.uniform(0.1, 3.0), 2),
        "has_health_insurance": rng.random() < 0.2,
    }


def stratum_pmjay_category(rng: random.Random) -> Dict[str, Any]:
    """Category boundary — SC/ST (eligible) vs OBC/BPL/General (not)."""
    return {
        "age": rng.randint(18, 70),
        "income": rng.randint(50_000, 400_000),
        "category": rng.choice(["SC", "ST", "OBC", "BPL", "General",
                                 "SC", "ST"]),   # over-weight eligible
        "state": rng.choice(STATES),
        "owns_house": rng.random() < 0.3,
        "owns_lpg": rng.random() < 0.4,
        "land_owned_hectares": round(rng.uniform(0.0, 3.0), 2),
        "has_health_insurance": rng.random() < 0.25,  # exclusion boundary
    }


def stratum_nsap_age(rng: random.Random) -> Dict[str, Any]:
    """Age near the NSAP threshold of 60."""
    return {
        "age": rng.choice([
            rng.randint(55, 59),   # just under
            60,                    # exactly at threshold
            rng.randint(61, 80),   # clearly eligible
            rng.randint(30, 50),   # clearly not eligible
        ]),
        "income": rng.randint(50_000, 400_000),
        "category": rng.choice(CATEGORIES),
        "state": rng.choice(STATES),
        "owns_house": rng.random() < 0.3,
        "owns_lpg": rng.random() < 0.5,
        "land_owned_hectares": round(rng.uniform(0.0, 3.0), 2),
        "has_health_insurance": rng.random() < 0.2,
    }


def stratum_ujjwala_lpg(rng: random.Random) -> Dict[str, Any]:
    """LPG ownership and category boundary for Ujjwala."""
    return {
        "age": rng.randint(18, 70),
        "income": rng.randint(50_000, 500_000),
        "category": rng.choice(["BPL", "SC", "ST", "OBC", "General",
                                 "BPL", "SC", "ST"]),  # over-weight eligible
        "state": rng.choice(STATES),
        "owns_house": rng.random() < 0.4,
        "owns_lpg": rng.choice([True, False, False]),   # 2/3 LPG-free
        "land_owned_hectares": round(rng.uniform(0.0, 3.0), 2),
        "has_health_insurance": rng.random() < 0.2,
    }


def stratum_pmkisan_land(rng: random.Random) -> Dict[str, Any]:
    """Land and income boundary for PM-KISAN."""
    land = rng.choice([
        round(rng.uniform(0.1, 1.9), 2),   # under limit
        2.0,                                # exactly at limit
        round(rng.uniform(2.1, 5.0), 2),   # over limit
    ])
    income = rng.choice([
        rng.randint(100_000, 249_999),   # under exclusion
        250_000,                         # at exclusion
        rng.randint(250_001, 400_000),   # over exclusion
    ])
    return {
        "age": rng.randint(18, 75),
        "income": income,
        "category": rng.choice(CATEGORIES),
        "state": rng.choice(STATES),
        "owns_house": rng.random() < 0.35,
        "owns_lpg": rng.random() < 0.4,
        "land_owned_hectares": land,
        "has_health_insurance": rng.random() < 0.15,
    }


def stratum_multi_disqualified(rng: random.Random) -> Dict[str, Any]:
    """High-income / house-owning profiles that fail most schemes."""
    return {
        "age": rng.randint(25, 65),
        "income": rng.randint(500_000, 1_500_000),
        "category": rng.choice(["General", "OBC", "General"]),
        "state": rng.choice(STATES),
        "owns_house": True,
        "owns_lpg": True,
        "land_owned_hectares": round(rng.uniform(3.0, 10.0), 2),
        "has_health_insurance": rng.random() < 0.5,
    }


def stratum_edge_minor(rng: random.Random) -> Dict[str, Any]:
    """Minor applicants (age < 18) — fail PMAY, NSAP age checks."""
    return {
        "age": rng.randint(10, 17),
        "income": rng.randint(50_000, 200_000),
        "category": rng.choice(["SC", "ST", "BPL", "OBC"]),
        "state": rng.choice(STATES),
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": round(rng.uniform(0.1, 1.5), 2),
        "has_health_insurance": False,
    }


# ─────────────────────────────────────────────────────────────
# Profile generation: stratified mix
# ─────────────────────────────────────────────────────────────

def generate_profiles(n: int, seed: int) -> List[Dict[str, Any]]:
    """
    Generates n unique profiles using a stratified approach:
      40% purely random
      60% from the 7 targeted strata (10% each, rounded)
    """
    rng = random.Random(seed)

    strata_fns = [
        stratum_pmay_boundary,
        stratum_pmjay_category,
        stratum_nsap_age,
        stratum_ujjwala_lpg,
        stratum_pmkisan_land,
        stratum_multi_disqualified,
        stratum_edge_minor,
    ]

    n_random  = int(n * 0.40)
    n_strata  = n - n_random
    per_stratum = n_strata // len(strata_fns)
    remainder   = n_strata % len(strata_fns)

    profiles = []

    # Pure random
    for _ in range(n_random):
        profiles.append(random_profile(rng))

    # Targeted strata
    for i, fn in enumerate(strata_fns):
        count = per_stratum + (1 if i < remainder else 0)
        for _ in range(count):
            profiles.append(fn(rng))

    # Shuffle to avoid scheme-order bias
    rng.shuffle(profiles)
    return profiles


# ─────────────────────────────────────────────────────────────
# Main experiment runner
# ─────────────────────────────────────────────────────────────

def main():
    print("Generating synthetic profiles...")
    profiles = generate_profiles(N_PROFILES, SEED)
    print(f"  ✓ {len(profiles)} profiles generated (seed={SEED})")

    print("\nLoading Phi-3 Mini Instruct (once for all experiments)...")
    llm = Phi3LLM()

    total = len(profiles) * len(SCHEME_IDS)
    counter = 0
    overall_start = time.perf_counter()

    print(f"\nStarting sweep: {len(SCHEME_IDS)} schemes × {len(profiles)} profiles = {total} experiments\n")

    for scheme_id in SCHEME_IDS:
        scheme = load_scheme(scheme_id)
        scheme_start = time.perf_counter()
        scheme_hallucinations = 0

        for profile in profiles:
            counter += 1

            # --- Rule engine (deterministic, ground truth) ---
            evaluation = evaluate_scheme(profile, scheme)
            structured_block = format_explanation_block(scheme["scheme_name"], evaluation)

            # --- Proposed system: LLM-guided explanation ---
            prompt = build_explanation_prompt(scheme["scheme_name"], evaluation)
            full_explanation = llm.generate(prompt, max_tokens=80).strip()

            # --- Baseline: LLM decides eligibility directly ---
            baseline_output = run_baseline(llm, scheme_id, scheme["scheme_name"], profile)

            # Quick inline hallucination check for progress display
            bl = baseline_output.lower()
            if "not eligible" in bl:
                baseline_pred = False
            elif "eligible" in bl:
                baseline_pred = True
            else:
                baseline_pred = None

            gt = evaluation["eligible"]
            is_hallucination = (baseline_pred is not None) and (baseline_pred != gt)
            if is_hallucination:
                scheme_hallucinations += 1

            eligible_str = "eligible    " if gt else "NOT eligible"
            hall_str = " ⚠ HALLUCINATION" if is_hallucination else ""
            print(f"  [{counter:>3}/{total}] {scheme_id:<10} → {eligible_str}{hall_str}")

            # --- Log ---
            log_experiment(
                scheme_id=scheme_id,
                scheme_name=scheme["scheme_name"],
                user_profile=profile,
                rule_engine_result=evaluation,
                proposed_system_explanation=full_explanation,
                baseline_llm_output=baseline_output.strip(),
                model_metadata=MODEL_METADATA,
                verbose=False,
            )

        scheme_elapsed = time.perf_counter() - scheme_start
        print(f"  ⇒ {scheme_id} done in {scheme_elapsed:.0f}s  |  baseline hallucinations: {scheme_hallucinations}\n")

    overall_elapsed = time.perf_counter() - overall_start
    print(f"Done. {total} experiments logged → logs/experiments.jsonl  ({overall_elapsed:.0f}s total)")
    print(f"Re-run evaluation: python analysis/evaluate.py")


if __name__ == "__main__":
    main()
