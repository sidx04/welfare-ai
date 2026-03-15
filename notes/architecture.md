# Welfare-AI: System Architecture

The following ASCII diagram illustrates the dual-pipeline architecture used for comparing a hybrid **Rule-Engine + LLM Explanation** system (Proposed) against a **Direct LLM Decision** system (Baseline).

```text
                                  ┌────────────────────┐
                                  │   USER PROFILES    │
                                  │ (Real or Synthetic)│
                                  └──────────┬─────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      │                                             │
                      ▼                                             ▼
        ┌────────────────────────────┐                ┌────────────────────────────┐
        │     PROPOSED SYSTEM        │                │      BASELINE SYSTEM       │
        │   (Symbolic + Neural)      │                │       (Pure Neural)        │
        └─────────────┬──────────────┘                └─────────────┬──────────────┘
                      │                                             │
        ┌─────────────▼──────────────┐                ┌─────────────▼──────────────┐
        │       SCHEME LOADER        │                │       SCHEME LOADER        │
        │  (Loads JSON Conditions)    │                │  (Loads Scheme Context)    │
        └─────────────┬──────────────┘                └─────────────┬──────────────┘
                      │                                             │
        ┌─────────────▼──────────────┐                ┌─────────────▼──────────────┐
        │       RULE ENGINE          │                │       PROMPT BUILDER       │
        │   (Deterministic logic)    │                │  (Profile + Scheme Text)   │
        └─────────────┬──────────────┘                └─────────────┬──────────────┘
                      │                                             │
        ┌─────────────▼──────────────┐                ┌─────────────▼──────────────┐
        │       RE REASONING         │                │        PHI-3 LLM           │
        │ (Verdict + Rule Trace)     │                │  (Direct Eligibility)      │
        └─────────────┬──────────────┘                └─────────────┬──────────────┘
                      │                                             │
        ┌─────────────▼──────────────┐                              │
        │       PROMPT BUILDER       │                              │
        │  (Verdict + Trace Text)    │                              │
        └─────────────┬──────────────┘                              │
                      │                                             │
        ┌─────────────▼──────────────┐                              │
        │         PHI-3 LLM          │                              │
        │    (Sentence Generation)   │                              │
        └─────────────┬──────────────┘                              │
                      │                                             │
                      │                                             │
                      └──────────────────────┬──────────────────────┘
                                             │
                                             ▼
                              ┌────────────────────────────┐
                              │     EXPERIMENT LOGGER      │
                              │ (logs/experiments.jsonl)   │
                              └──────────────┬─────────────┘
                                             │
                        ┌────────────────────┴────────────────────┐
                        │                                         │
                        ▼                                         ▼
          ┌────────────────────────────┐            ┌────────────────────────────┐
          │      LOG ANALYZER          │            │     VISUALIZATION          │
          │  (analysis/evaluate.py)    │            │  (analysis/visualize.py)   │
          └─────────────┬──────────────┘            └─────────────┬──────────────┘
                        │                                         │
                        ▼                                         ▼
          ┌────────────────────────────┐            ┌────────────────────────────┐
          │   METRICS (results.json)   │            │    CHARTS (PNG Output)     │
          │  Accuracy/Faithfulness     │            │   Comparative Graphs       │
          └────────────────────────────┘            └────────────────────────────┘
```

## Component Definitions

### 1. Data Layer
*   **User Profiles**: JSON objects containing attributes like [age](file:///Users/sid/Workstation/Code-Projects/welfare-ai/run_synthetic_experiments.py#142-159), `income`, [category](file:///Users/sid/Workstation/Code-Projects/welfare-ai/run_synthetic_experiments.py#127-140), and `land_owned_hectares`.
*   **Schemes**: Definition files in `schemes/*.json` prescribing `if-then` conditions for eligibility.

### 2. Proposed System (Hybrid Architecture)
*   **Rule Engine**: A deterministic symbolic filter ([rule_engine.py](file:///Users/sid/Workstation/Code-Projects/welfare-ai/rule_engine.py)) that executes Boolean logic against profile data.
*   **Trace Extraction**: Captures which specific rules passed or failed (e.g., "Income > 3L").
*   **LLM Explainer**: A Phi-3 model translates the symbolic trace into natural language. It **never** decides eligibility; it only explains the Engine's decision.

### 3. Baseline System (LLM Direct)
*   **Zero-Shot Evaluator**: The LLM is provided the scheme name and user profile, then asked to decide eligibility directly. This path simulates the current industry "naive" deployment of LLMs for policy tasks.

### 4. Evaluation Infrastructure
*   **Metric Engine**: Compares the Baseline decision against the Rule Engine's ground truth.
*   **Faithfulness Checker**: Verifies if the LLM's natural language explanation correctly cites the facts used by the Rule Engine.
