from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# Reuse your existing modules (NO duplication)
from scheme_loader import load_scheme
from rule_engine import evaluate_scheme
from llm.phi3 import Phi3LLM
from llm.prompts import build_explanation_prompt, format_explanation_block
from baseline.run_baseline import run_baseline

# -----------------------------
# App Init
# -----------------------------

app = FastAPI(title="Explainable Eligibility Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load LLM once
llm = Phi3LLM()


# -----------------------------
# Request Schema
# -----------------------------

class EvaluationRequest(BaseModel):
    scheme_id: str
    profile: Dict[str, Any]


# -----------------------------
# Core Endpoint (Proposed System)
# -----------------------------

@app.post("/evaluate")
def evaluate(req: EvaluationRequest):
    try:
        scheme = load_scheme(req.scheme_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Scheme not found")

    # --- SAME FLOW AS main.py ---

    evaluation = evaluate_scheme(req.profile, scheme)

    structured_block = format_explanation_block(
        scheme["scheme_name"],
        evaluation
    )

    prompt = build_explanation_prompt(
        scheme["scheme_name"],
        evaluation
    )

    llm_sentence = llm.generate(prompt, max_tokens=80)
    full_explanation = llm_sentence.strip()

    return {
        "scheme_name": scheme["scheme_name"],
        "eligible": evaluation.get("eligible", False),
        "trace": evaluation.get("trace", []),
        "structured_explanation": structured_block,
        "llm_explanation": full_explanation,
    }


# -----------------------------
# Baseline Endpoint (VERY USEFUL FOR DEMO)
# -----------------------------

@app.post("/baseline")
def baseline(req: EvaluationRequest):
    try:
        scheme = load_scheme(req.scheme_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Scheme not found")

    output = run_baseline(
        llm,
        req.scheme_id,
        scheme["scheme_name"],
        req.profile
    )

    return {
        "scheme_name": scheme["scheme_name"],
        "baseline_output": output.strip()
    }


# -----------------------------
# Health Check
# -----------------------------

@app.get("/")
def root():
    return {"message": "API running"}