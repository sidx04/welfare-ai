from scheme_loader import load_scheme
from rule_engine import evaluate_scheme
from llm.phi3 import Phi3LLM
from llm.prompts import build_explanation_prompt, format_explanation_block
from baseline.run_baseline import run_baseline
from experiment_logging.experiment_logger import log_experiment
import json

user_profile = {
    "age": 35,
    "income": 450000,
    "category": "SC",
    "state": "Karnataka",
    "owns_house": False,
    "owns_lpg": False,
    "land_owned_hectares": 1.5,
    "has_health_insurance": False
}

scheme_id = "pmay"

scheme = load_scheme(scheme_id)

llm = Phi3LLM()


# ------------------------
# Proposed System
# ------------------------

evaluation = evaluate_scheme(user_profile, scheme)

# Deterministic structured block — never touches the LLM
structured_block = format_explanation_block(scheme["scheme_name"], evaluation)

# LLM generates a single explanation sentence
prompt = build_explanation_prompt(scheme["scheme_name"], evaluation)
llm_sentence = llm.generate(prompt, max_tokens=80)
full_explanation = llm_sentence.strip()

print("\n=== Rule Engine Result ===")
print(json.dumps(evaluation, indent=2))

print("\n=== Explanation (Proposed System) ===")
print(structured_block)
print()
print(full_explanation)


# ------------------------
# Baseline System
# ------------------------

baseline_output = run_baseline(
    llm,
    scheme_id,
    scheme["scheme_name"],
    user_profile
)

print("\n=== Baseline LLM Decision ===")
print(baseline_output)


# ------------------------
# Experiment Logging
# ------------------------

model_metadata = {
    "model": "phi-3-mini-4k-instruct-4bit",
    "temperature": 0,
    "max_tokens": 80
}

log_experiment(
    scheme_id=scheme_id,
    scheme_name=scheme["scheme_name"],
    user_profile=user_profile,
    rule_engine_result=evaluation,
    proposed_system_explanation=full_explanation,
    baseline_llm_output=baseline_output.strip(),
    model_metadata=model_metadata
)