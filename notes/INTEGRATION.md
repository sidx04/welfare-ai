# 🔗 Integration Guide: Hallucination Detection + Counterfactual Engine

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WELFARE-AI SYSTEM                           │
└─────────────────────────────────────────────────────────────────────┘

                        User Profile
                             │
                    ┌────────▼────────┐
                    │  Rule Engine    │
                    │ (Ground Truth)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Evaluation      │
                    │ Result (trace)  │
                    └────────┬────────┘
                    ┌────────┴────────┐
                    │                 │
            ┌───────▼───────┐  ┌──────▼──────┐
            │  Eligibility  │  │   LLM...    │
            │  Eligible:    │  │ Explanation │
            │  Yes/No       │  └──────┬──────┘
            └───────┬───────┘         │
                    │         ┌───────▼────────┐
                    │         │ HALLUCINATION  │
                    │         │DETECTOR        │
                    │         │(NEW)           │
                    │         ├─ Type         │
                    │         ├─ Count        │
                    │         ├─ Severity     │
                    │         └────────┬───────┘
                    │                   │
                    └──────────┬────────┘
                               │
                        ┌──────▼────────┐
                        │ Log to JSONL  │
                        │ (experiment   │
                        │  record)      │
                        └──────────────┘

                IF NOT ELIGIBLE:
                
            ┌────────────────────────────┐
            │  WHAT-IF ENGINE (NEW)      │
            ├────────────────────────────┤
            │ 1. Parse Failed Conditions │
            │ 2. Generate Scenarios      │
            │ 3. Score Feasibility       │
            │ 4. Rank by Practicality    │
            └────────────────┬───────────┘
                             │
                ┌────────────▼─────────┐
                │ Counterfactuals:    │
                ├─ Suggested Changes  │
                ├─ Feasibility Rank   │
                ├─ Rationale          │
                └────────────┬────────┘
                             │
            ┌────────────────▼──────────┐
            │   Backend API Endpoints   │
            ├──────────────────────────┤
            │ /counterfactuals         │
            │ /counterfactuals-all     │
            └────────────────┬─────────┘
                             │
            ┌────────────────▼──────────┐
            │    Frontend Display       │
            ├──────────────────────────┤
            │ 💭 "How to become       │
            │    eligible?"            │
            │ - Feasibility rank       │
            │ - Suggested changes      │
            │ - Rationale              │
            └──────────────────────────┘


                  ANALYSIS PIPELINE
                    (For Research)

            ┌──────────────────────────┐
            │  Experiment JSONL File   │
            │  (500+ records)          │
            └────────────┬─────────────┘
                         │
            ┌────────────▼────────────┐
            │ analysis/evaluate.py    │
            ├────────────────────────┤
            │ Aggregate Metrics:     │
            │ - Hallucination Rate   │ (NEW)
            │ - Per-Scheme HR        │ (NEW)
            │ - Avg Severity         │ (NEW)
            │ - Decision Accuracy    │
            │ - Faithfulness         │
            └────────────┬───────────┘
                         │
            ┌────────────▼────────────┐
            │ analysis/results.json   │
            │ (Full Report)           │
            └────────────────────────┘
```

---

## Data Flow Example

### Scenario: User evaluation for PM-KISAN

```
INPUT: 
  Profile = {
    age: 35,
    income: 300000,      ← FAILS: > 250000 limit
    category: "SC",
    land_owned_hectares: 2.5,  ← FAILS: > 2.0 limit
    ...
  }
  Scheme = PM-KISAN

STEP 1: Rule Engine Evaluation
  ✓ Check age >= 18        → PASS
  ✓ Check category        → PASS
  ✗ Check income <= 250k   → FAIL (actual: 300k)
  ✗ Check land <= 2ha      → FAIL (actual: 2.5ha)
  
  Result: eligible = False, trace = [...]

STEP 2: LLM Explanation
  "The applicant is not eligible for PM-KISAN because
   their income is too high and they own more than 2 hectares."

STEP 3: Hallucination Detector
  ✓ No false criteria detected
  ✓ No wrong thresholds detected
  ✓ No inverted logic detected
  → has_hallucinations = False
  → severity_score = 0.0

STEP 4: What-If Engine (since not eligible)
  Scenario 1:
    field: "income"
    current_value: 300000
    required_value: 250000
    suggested_value: 245000  (with 2% buffer)
    feasibility_score: 0.4   (hard to change income)
    rationale: "Reduce income from 300,000 to 245,000..."
  
  Scenario 2:
    field: "land_owned_hectares"
    current_value: 2.5
    required_value: 2.0
    suggested_value: 1.95
    feasibility_score: 0.3   (hard to reduce land)
    rationale: "Reduce holdings from 2.5 to 1.95 hectares..."
  
  Sorted by feasibility:
  [Scenario 1 (0.4), Scenario 2 (0.3)]

STEP 5: Log to JSONL
  {
    "timestamp": "2026-04-06T12:00:00Z",
    "scheme_id": "pmkisan",
    "user_profile": {...},
    "rule_engine_result": {
      "eligible": false,
      "trace": [...]
    },
    "proposed_system_explanation": "...",
    "hallucination_analysis": {
      "has_hallucinations": false,
      "hallucination_count": 0,
      "severity_score": 0.0,
      "hallucinations": []
    }
  }

STEP 6: Backend API
  /counterfactuals returns:
  {
    "scheme_id": "pmkisan",
    "is_eligible": false,
    "scenarios": [
      {field: "income", feasibility_score: 0.4, ...},
      {field: "land_owned_hectares", feasibility_score: 0.3, ...}
    ],
    "summary": "Most feasible fix: income reduction"
  }

STEP 7: Frontend Display
  ┌─ PM-KISAN Samman Nidhi
  ❌ Not Eligible
  
  💭 How to become eligible? (CLICK HERE)
  │
  ├─ 🟡 INCOME (Moderately Feasible)
  │  Current: ₹3,00,000
  │  Target: ₹2,45,000
  │  💡 Reduce income by ₹55,000 (save ~18%)
  │
  └─ 🔴 LAND (Difficult)
     Current: 2.5 hectares
     Target: 1.95 hectares
     💡 Reduce holdings by 0.55 ha
```

---

## Integration Points

### 1. Experiment Logger Integration

```python
# In experiment_logging/experiment_logger.py
def log_experiment(...):
    # Automatic hallucination detection
    detector = HallucinationDetector()
    hallucination_result = detector.detect_hallucinations(
        proposed_system_explanation,
        trace
    )
    
    record["hallucination_analysis"] = hallucination_result
    
    # Write to JSONL
    with open(EXPERIMENTS_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")
```

**When it runs:**
- Every time an experiment is logged
- Both in `run_experiments.py` and `run_synthetic_experiments.py`
- Happens automatically without user intervention

### 2. Analysis Integration

```python
# In analysis/evaluate.py
def evaluate(log_path):
    # Read JSONL
    for log in jsonl_records:
        hallucination_analysis = log.get("hallucination_analysis", {})
        
        if hallucination_analysis.get("has_hallucinations"):
            per_scheme_proposed_hallucination[scheme] += 1
        
        severity = hallucination_analysis.get("severity_score", 0.0)
        per_scheme_hallucination_severity[scheme] += severity
    
    # Report metrics
    hallucination_rate = overall_hallucinations / total
    
    results_json["proposed_hallucination_rate"] = hallucination_rate
    results_json["per_scheme"]["hallucination_rate"] = scheme_rate
```

**Output:**
- Detailed results.json with hallucination breakdowns
- Summary stats comparing proposed vs. baseline

### 3. Backend Integration

```python
# In api/backend.py
@app.post("/counterfactuals")
def counterfactuals(req: GapAnalysisRequest):
    return evaluate_counterfactuals(req.scheme_id, req.profile)

@app.post("/counterfactuals-all")
def counterfactuals_all(req: EvaluationAllRequest):
    return evaluate_all_counterfactuals(req.profile)

# In api/features.py
def evaluate_counterfactuals(scheme_id, profile):
    evaluation = evaluate_scheme(profile, scheme)
    
    if evaluation["eligible"]:
        return {"is_eligible": True, ...}
    
    what_if_result = generate_what_if_explanations(
        profile,
        evaluation["trace"]
    )
    
    return {
        "scenarios": what_if_result["scenarios"],
        "summary": what_if_result["summary"],
        ...
    }
```

### 4. Frontend Integration

```javascript
// In frontend/app.js
async function handleEvaluate(e) {
    const data = await postRequest("/evaluate", {scheme_id, profile});
    updateUI(renderProposed(data));
    
    if (!data.eligible) {
        // NEW: Load counterfactuals
        const cfData = await postRequest("/counterfactuals", {
            scheme_id: data.scheme_id,
            profile
        });
        document.getElementById(`counterfactuals-${scheme_id}`).innerHTML 
            = renderCounterfactuals(cfData);
        
        // EXISTING: Load gap analysis
        const gapData = await postRequest("/gap-analysis", {...});
        // ...
    }
}

function renderCounterfactuals(data) {
    // Display scenarios ranked by feasibility
    // Show 🟢 / 🟡 / 🔴 badges
    // Display rationale and suggested values
}
```

---

## Workflow Examples

### For Researchers Running Experiments

```bash
# 1. Generate experiments
python run_synthetic_experiments.py

# 2. Automatically logs hallucinations to JSONL

# 3. Analyze results
python analysis/evaluate.py

# 4. Check results.json for:
#    - proposed_hallucination_rate
#    - baseline_hallucination_rate
#    - per_scheme hallucination analysis
```

### For Users Using the Web UI

```
1. Fill profile form
2. Select scheme
3. Click "Evaluate"
4. See: ❌ Not Eligible
5. Click "💭 How to become eligible?"
6. See: Ranked improvement paths
7. Click on scenario to see details
```

### For Backend Developers

```python
from api.features import evaluate_counterfactuals

result = evaluate_counterfactuals(
    scheme_id="pmkisan",
    profile={...}
)

# Use scenarios to:
# - Show in UI
# - Generate PDFs
# - Send SMS notifications
# - Build dashboards
```

---

## Performance Notes

**Hallucination Detection:**
- ~5ms per explanation (lightweight keyword matching)
- Negligible overhead when logging

**What-If Generation:**
- ~10ms per scheme (finite number of conditions)
- Backend call: ~50-100ms for single scheme
- Backend call: ~250-500ms for all 5 schemes

---

## Testing Strategy

### Unit Tests
```bash
# Test hallucination detector
python -c "
from llm.hallucination_detector import HallucinationDetector
detector = HallucinationDetector()
result = detector.detect_hallucinations(explanation, trace)
assert 'severity_score' in result
"

# Test what-if engine
python -c "
from llm.what_if_engine import WhatIfEngine
engine = WhatIfEngine()
scenarios = engine.generate_scenarios(profile, trace)
assert all('feasibility_score' in s for s in scenarios)
"
```

### Integration Tests
```bash
python test_hallucination_detection.py    # On JSONL data
python demo_what_if_scenarios.py          # Shows scenarios
```

### End-to-End Test
```bash
1. uvicorn api.backend:app --reload
2. Open http://127.0.0.1:8000/
3. Fill profile
4. Check:
   - Hallucination analysis in logs
   - Counterfactual scenarios displayed
```

---

## Monitoring & Metrics

```
Hallucination Dashboard:
├─ Overall HR: 5.2%
├─ Per-scheme breakdown
├─ Severity distribution
└─ Trend over time (if running continuously)

Counterfactual Dashboard:
├─ Schemes with feasible improvements: 45%
├─ Common improvement patterns
├─ Feasibility distribution
└─ Most impactful changes
```

---

## Extensibility

### Adding New Hallucination Types

```python
# In llm/hallucination_detector.py
def _detect_custom_hallucination(self, ...):
    # Add logic
    return hallucination_dict

# In detect_hallucinations() method:
custom_hallucinations = self._detect_custom_hallucination(...)
hallucinations.extend(custom_hallucinations)
```

### Modifying Feasibility Weights

```python
# In llm/what_if_engine.py
FEASIBILITY_WEIGHTS = {
    "income": 0.4,      # Modify based on user research
    "new_field": 0.7,   # Add new fields
}

# Or dynamically:
def get_feasibility_for_field(field, user_context):
    # User can't reduce income if unemployed
    # User can easily acquire LPG if state subsidizes
    ...
```

### Custom Rationale Generation

```python
# In llm/what_if_engine.py
def _get_rationale_decrease(field, actual, suggested, required):
    # Add field-specific logic
    if field == "income":
        return f"Consider gig work or side income..."
    # or call LLM for custom explanations
```

---

## Summary

The system now has:

✅ **Hallucination Detection**
- Automatic on every experiment
- 4 detection types
- Severity scoring
- Integrated with evaluator

✅ **Counterfactual Scenarios**
- Generated for ineligible users
- Ranked by feasibility
- Clear actionable guidance
- Backend + Frontend integrated

✅ **Research Metrics**
- Hallucination rate tracking
- Per-scheme analysis
- Baseline comparison

✅ **Modular Design**
- Each component independent
- Easy to extend/customize
- Clean interfaces
