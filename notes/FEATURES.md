# Welfare-AI Advanced Features
## Hallucination Detection & Counterfactual Scenarios

This document describes two major feature additions to welfare-ai:

1. **Hallucination Detection** – Validates LLM explanations against ground truth
2. **Counterfactual Scenarios (What-If Engine)** – Generates improvement paths for ineligible users

---

## 1. Hallucination Detection

### Overview

Detects when LLM explanations contain information that contradicts the rule trace (ground truth).

**Hallucination Types:**
- **False Criteria**: Mentions criteria not in the rule trace
- **Wrong Thresholds**: Cites correct field but incorrect numeric value
- **Inverted Logic**: Gets the sense backwards (must own vs. must NOT own)
- **Fake Benefits**: Claims benefits/features not in the scheme

### Where It's Used

**Automatic in Experiment Logger:**
```python
# In experiment_logging/experiment_logger.py
log_experiment(
    scheme_id="pmay",
    scheme_name="Pradhan Mantri Awas Yojana",
    user_profile=profile,
    rule_engine_result=evaluation,
    proposed_system_explanation=llm_output,
    baseline_llm_output=baseline_output,
    model_metadata=metadata,
    # ↑ Hallucination detection runs automatically
)
```

**In Analysis/Evaluation:**
```python
# In analysis/evaluate.py
# Computes:
# - proposed_hallucination_rate: % of explanations with hallucinations
# - per_scheme hallucination_rate and avg_severity
```

### Module: `llm/hallucination_detector.py`

**Main Class: `HallucinationDetector`**

```python
from llm.hallucination_detector import HallucinationDetector

detector = HallucinationDetector()

# Detect hallucinations in an explanation
result = detector.detect_hallucinations(
    llm_explanation="The applicant is eligible due to meeting income...",
    rule_trace=[
        {
            "field": "income",
            "operator": "<=",
            "required": 300000,
            "actual": 150000,
            "passed": True,
            "description": "Annual income must be within EWS limit (₹3 lakh)"
        },
        # ... more trace items
    ]
)

print(result)
# {
#     "has_hallucinations": False,
#     "hallucination_count": 0,
#     "severity_score": 0.0,
#     "hallucinations": []
# }
```

### Results in JSONL

Each experiment record now includes:
```json
{
    "timestamp": "2026-04-06T12:00:00Z",
    "scheme_id": "pmay",
    ...
    "proposed_system_explanation": "...",
    "hallucination_analysis": {
        "has_hallucinations": false,
        "hallucination_count": 0,
        "severity_score": 0.0,
        "hallucinations": []
    }
}
```

### Evaluation Results

Run evaluation to see hallucination rates:
```bash
python analysis/evaluate.py --log logs/experiments.jsonl
```

Output (excerpt):
```
─── OVERALL METRICS ──────────────────────────────────────────────────────
  Metric                      Proposed System  Baseline LLM
  Decision Accuracy           100.0%           75.3%
  Explanation Hallucination    5.2%            22.1%
  Explanation Faithfulness     98.1%           87.4%

─── PER-SCHEME BREAKDOWN ─────────────────────────────────────────────────
  Scheme                           Total  Proposed HR    Baseline HR
  Pradhan Mantri Awas Yojana          20      2.5%          20.0%
  Ayushman Bharat – PM-JAY            20      8.0%          25.0%
  ...
```

---

## 2. Counterfactual Scenarios (What-If Engine)

### Overview

Transforms passive ineligibility ("You are not eligible") into actionable guidance ("Here's how to become eligible").

For each failed condition, the engine recommends:
- **Minimal Change**: What specific value change is needed
- **Feasibility Score**: How practical/achievable the change is (0.0-1.0)
- **Rationale**: Human-friendly explanation of the change

### Example

**Input:** User ineligible for PM-KISAN because:
- Income exceeds ₹2.5L  (actual ₹3L)
- Landholding is 2.5ha (needs ≤ 2ha)

**Output:**
```
🎯 Path to Eligibility

Your income exceeds PM-KISAN limit.
If your income were ₹2.4 lakh, you would be eligible.

Feasibility: 🟡 Moderately Feasible
Rationale: Reduce income from ₹3,00,000 to ₹2,40,000 (save ₹60,000 or ~20%)

---

Your land holding exceeds PM-KISAN limit.
If your land were 1.9 hectares, you would be eligible.

Feasibility: 🔴 Difficult
Rationale: Reduce holdings from 2.5 to 1.9 hectares
```

### Module: `llm/what_if_engine.py`

**Main Class: `WhatIfEngine`**

```python
from llm.what_if_engine import WhatIfEngine, generate_what_if_explanations

engine = WhatIfEngine()

# Generate scenarios for a failed evaluation
scenarios = engine.generate_scenarios(
    profile={
        "age": 30,
        "income": 300000,
        "category": "SC",
        ...
    },
    rule_trace=[
        {
            "field": "income",
            "operator": "<=",
            "required": 250000,
            "actual": 300000,
            "passed": False,
            ...
        },
        ...
    ]
)

# Returns sorted by feasibility (highest first)
# [
#     {
#         "field": "income",
#         "current_value": 300000,
#         "required_value": 250000,
#         "suggested_value": 245000,  # With buffer
#         "feasibility_score": 0.4,
#         "feasibility_label": "🟡 Moderately Feasible",
#         "rationale": "Reduce income from 300000 to 245000..."
#     }
# ]
```

### Backend API

**New Endpoints:**

#### POST `/counterfactuals`
```json
{
    "scheme_id": "pmkisan",
    "profile": { ... }
}
```

Response:
```json
{
    "scheme_id": "pmkisan",
    "scheme_name": "PM-KISAN Samman Nidhi",
    "is_eligible": false,
    "scenarios": [
        {
            "field": "income",
            "current_value": 300000,
            "required_value": 250000,
            "suggested_value": 245000,
            "feasibility_score": 0.4,
            "feasibility_label": "🟡 Moderately Feasible",
            "rationale": "Reduce income from 300,000 to 245,000..."
        }
    ],
    "summary": "Most feasible fix: income reduction",
    "multiple_paths": true,
    "feasible_paths": [ ... ]  // scenarios with score >= 0.5
}
```

#### POST `/counterfactuals-all`
```json
{
    "profile": { ... }
}
```

Response:
```json
{
    "profile": { ... },
    "summary": {
        "eligible": 2,
        "have_feasible_improvements": 1,
        "no_feasible_improvements": 2
    },
    "results": {
        "eligible": [
            {
                "scheme_id": "ujjwala",
                "scheme_name": "Pradhan Mantri Ujjwala Yojana"
            }
        ],
        "have_feasible_improvements": [
            {
                "scheme_id": "pmkisan",
                "scheme_name": "PM-KISAN Samman Nidhi",
                "top_improvement": { ... },
                "count_feasible": 1
            }
        ],
        "no_feasible_improvements": [
            {
                "scheme_id": "pmjay",
                "scheme_name": "Ayushman Bharat – PM-JAY",
                "summary": "Change is not practical (categories are fixed at registration)"
            }
        ]
    }
}
```

### Frontend Integration

The web UI now shows:

1. **"💭 How to become eligible?" tab** (NEW)
   - Displays counterfactual scenarios
   - Ranked by feasibility (🟢 → 🟡 → 🔴)
   - Shows minimal changes needed

2. **"🔍 What are the specific gaps?" tab** (EXISTING, repositioned)
   - Gap analysis (distance to passing)
   - Detailed condition failures

**Example UI Flow:**
```
Pradhan Mantri Awas Yojana
❌ Not Eligible

Explanation
> Your income exceeds the EWS limit...

💭 How to become eligible? (Click to expand)
──────────────────────────────────────────────
🎯 Path to Eligibility

Most feasible fix: Reduce income from ₹3L to ₹2.95L

income [🟡 Moderately Feasible]
Current: ₹3,00,000
Target: ₹2,95,000
💡 Reduce income from 300,000 to 295,000 (save ₹5,000 or ~1.7%)

🔍 What are the specific gaps? (Click to expand)
─────────────────────────────────────────────────
[Gap analysis details...]
```

### Demo Script

Run the demo to see counterfactual scenarios in action:

```bash
python demo_what_if_scenarios.py
```

Output:
```
────────────────────────────────────────────────────────────────────────────────
  COUNTERFACTUAL SCENARIO DEMO
────────────────────────────────────────────────────────────────────────────────

📋 Profile: High-income farmer
────────────────────────────────────────────────────────────────────────────────

  ❌ Pradhan Mantri Awas Yojana: Not eligible
     Status: not eligible
     1 improvement path(s) identified:

       1. 🟡 Moderately Feasible
          Field: income
          Change: 350000 → 294000
          Rationale: Reduce income from 350,000 to 294,000 (save ₹56,000 or ~16.0%)
```

### Feasibility Scoring

Field feasibilities (0.0 = impossible, 1.0 = easy):

| Field | Score | Notes |
|-------|-------|-------|
| `has_health_insurance` | 0.8 | Easy – can enroll |
| `owns_lpg` | 0.7 | Easy – can acquire connection |
| `owns_house` | 0.6 | Moderate – can sell |
| `income` | 0.4 | Hard – requires income change |
| `land_owned_hectares` | 0.3 | Hard – requires land purchase |
| `age` | 0.1 | Very hard – cannot reverse |
| `category` | 0.05 | Essentially impossible |
| `state` | 0.0 | Impossible without relocation |

Severity levels:
- 🟢 **Highly Feasible**: score ≥ 0.7
- 🟡 **Moderately Feasible**: score ∈ [0.4, 0.7)
- 🔴 **Difficult**: score < 0.4

---

## Usage Summary

### In Experiments

The hallucination detector runs automatically when logging experiments:

```python
# run_experiments.py or run_synthetic_experiments.py
log_experiment(
    scheme_id=scheme_id,
    scheme_name=scheme["scheme_name"],
    user_profile=profile,
    rule_engine_result=evaluation,
    proposed_system_explanation=explanation,
    baseline_llm_output=baseline_output,
    model_metadata=MODEL_METADATA,
)
# ← Hallucination analysis is added to the JSONL record
```

### In Analysis

```bash
# Run evaluation to see hallucination rates and counterfactual stats
python analysis/evaluate.py

# Results saved to analysis/results.json with:
# - proposed_hallucination_rate
# - per_scheme hallucination analysis
```

### In Backend API

```bash
# Start the API
uvicorn api.backend:app --reload

# Then use the new endpoints:
# POST /counterfactuals
# POST /counterfactuals-all
# (Hallucination analysis available in /evaluate responses)
```

### In Frontend

The web UI automatically loads and displays:
- Counterfactual scenarios (what-if paths)
- Hallucination detection results (in evaluation logs)
- Feasibility rankings

---

## References

- **Hallucination Detector**: `llm/hallucination_detector.py`
- **What-If Engine**: `llm/what_if_engine.py`
- **Backend Features**: `api/features.py`
- **Experiment Logger**: `experiment_logging/experiment_logger.py`
- **Evaluator**: `analysis/evaluate.py`
- **Demo**: `demo_what_if_scenarios.py`
