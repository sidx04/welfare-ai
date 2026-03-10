from scheme_loader import load_scheme
from rule_engine import evaluate_scheme
from llm.phi2 import Phi2LLM
from llm.prompts import build_explanation_prompt
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

scheme = load_scheme("pmay")

evaluation = evaluate_scheme(user_profile, scheme)

llm = Phi2LLM()

prompt = build_explanation_prompt(
    scheme_name=scheme["scheme_name"],
    evaluation=evaluation
)


print("\n=== Eligibility Result ===")
print(json.dumps(evaluation, indent=2))

print("\n=== Explanation ===")
explanation = llm.generate(prompt, max_tokens=60)
print(explanation)
