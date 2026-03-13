from baseline.llm_baseline import build_baseline_prompt
from baseline.scheme_descriptions import SCHEME_DESCRIPTIONS
from llm.phi3 import Phi3LLM


def run_baseline(llm, scheme_id, scheme_name, user_profile):

    rules_text = SCHEME_DESCRIPTIONS[scheme_id]

    prompt = build_baseline_prompt(
        scheme_name,
        rules_text,
        user_profile
    )

    response = llm.generate(prompt, max_tokens=80)

    return response