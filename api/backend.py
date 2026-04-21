from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware

from scheme_loader import load_scheme, list_scheme_ids
from rule_engine import evaluate_scheme
from llm.phi3 import Phi3LLM
from llm.prompts import build_explanation_prompt, format_explanation_block
from baseline.run_baseline import run_baseline
from api.features import (
    evaluate_what_if,
    evaluate_gap_analysis,
    evaluate_counterfactuals,
    evaluate_all_counterfactuals,
)


app = FastAPI(title="Explainable Eligibility Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = Phi3LLM()


class EvaluationRequest(BaseModel):
    scheme_id: str
    profile: Dict[str, Any]


class EvaluationAllRequest(BaseModel):
    profile: Dict[str, Any]


class WhatIfRequest(BaseModel):
    profile: Dict[str, Any]
    modifications: Dict[str, Any]  # fields to change


class GapAnalysisRequest(BaseModel):
    scheme_id: str
    profile: Dict[str, Any]


@app.post("/evaluate")
def evaluate(req: EvaluationRequest):
    try:
        scheme = load_scheme(req.scheme_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Scheme not found")

    evaluation = evaluate_scheme(req.profile, scheme)

    structured_block = format_explanation_block(scheme["scheme_name"], evaluation)

    prompt = build_explanation_prompt(scheme["scheme_name"], evaluation)

    llm_sentence = llm.generate(prompt, max_tokens=80)
    full_explanation = llm_sentence.strip()

    return {
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "eligible": evaluation.get("eligible", False),
        "status": evaluation.get("status", "not eligible"),
        "failed_reasons": evaluation.get("failed_reasons", []),
        "trace": evaluation.get("trace", []),
        "structured_explanation": structured_block,
        "llm_explanation": full_explanation,
    }


@app.post("/evaluate_all")
def evaluate_all(req: EvaluationAllRequest):
    scheme_ids = list_scheme_ids()
    if not scheme_ids:
        raise HTTPException(status_code=500, detail="No schemes configured")

    results = []
    for scheme_id in scheme_ids:
        scheme = load_scheme(scheme_id)
        evaluation = evaluate_scheme(req.profile, scheme)

        prompt = build_explanation_prompt(scheme["scheme_name"], evaluation)
        llm_sentence = llm.generate(prompt, max_tokens=80)
        full_explanation = llm_sentence.strip()

        results.append(
            {
                "scheme_id": scheme_id,
                "scheme_name": scheme["scheme_name"],
                "eligible": evaluation["eligible"],
                "status": evaluation["status"],
                "pass_ratio": evaluation["pass_ratio"],
                "failed_reasons": evaluation["failed_reasons"],
                "trace": evaluation["trace"],
                "structured_explanation": format_explanation_block(
                    scheme["scheme_name"], evaluation
                ),
                "llm_explanation": full_explanation,
            }
        )

    status_order = {"eligible": 0, "partially eligible": 1, "not eligible": 2}
    sorted_results = sorted(
        results,
        key=lambda item: (
            status_order.get(item["status"], 2),
            -item["pass_ratio"],
            item["scheme_name"].lower(),
        ),
    )

    return {
        "matches": sorted_results,
        "groups": {
            "eligible": [
                item for item in sorted_results if item["status"] == "eligible"
            ],
            "partially_eligible": [
                item
                for item in sorted_results
                if item["status"] == "partially eligible"
            ],
            "not_eligible": [
                item for item in sorted_results if item["status"] == "not eligible"
            ],
        },
    }


@app.post("/baseline")
def baseline(req: EvaluationRequest):
    try:
        scheme = load_scheme(req.scheme_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Scheme not found")

    output = run_baseline(llm, req.scheme_id, scheme["scheme_name"], req.profile)

    return {"scheme_name": scheme["scheme_name"], "baseline_output": output.strip()}


@app.post("/what-if")
def what_if(req: WhatIfRequest):
    """
    Evaluate profile with modifications against all schemes.
    Show which schemes become eligible/ineligible with the changes.
    """
    return evaluate_what_if(req.profile, req.modifications)


@app.post("/gap-analysis")
def gap_analysis(req: GapAnalysisRequest):
    """
    Analyze failed conditions for a scheme and rank by closeness to passing.
    Provides actionable suggestions for improvement.
    """
    try:
        return evaluate_gap_analysis(req.scheme_id, req.profile)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/counterfactuals")
def counterfactuals(req: GapAnalysisRequest):
    """
    Generate counterfactual "what-if" scenarios for a single scheme.
    Shows minimal changes needed to become eligible, ranked by feasibility.

    Returns:
        {
            "scheme_id": str,
            "scheme_name": str,
            "is_eligible": bool,
            "scenarios": List[
                {
                    "field": str,
                    "current_value": Any,
                    "required_value": Any,
                    "suggested_value": Any,
                    "feasibility_score": float (0-1),
                    "feasibility_label": str,
                    "rationale": str,
                }
            ],
            "summary": str,
            "multiple_paths": bool,
            "feasible_paths": List[Dict],
        }
    """
    try:
        return evaluate_counterfactuals(req.scheme_id, req.profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/counterfactuals-all")
def counterfactuals_all(req: EvaluationAllRequest):
    """
    Generate counterfactual scenarios for ALL schemes.
    Portfolio view showing eligibility and improvement paths across schemes.

    Returns schemes grouped by:
      - eligible: Already eligible
      - have_feasible_improvements: Can become eligible with practical changes
      - no_feasible_improvements: Would require impractical changes
    """
    try:
        return evaluate_all_counterfactuals(req.profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {"message": "API running"}
