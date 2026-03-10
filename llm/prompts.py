# def build_explanation_prompt(
#     scheme_name: str,
#     user_profile: dict,
#     evaluation_result: dict
# ) -> str:
#     return f"""
# You are an assistant explaining welfare eligibility decisions.
# Do NOT change the decision.
# Do NOT invent rules.

# Scheme:
# {scheme_name}

# User Profile:
# {user_profile}

# Eligibility Decision:
# {"Eligible" if evaluation_result["eligible"] else "Not Eligible"}

# Rule Evaluation Trace:
# {evaluation_result["trace"]}

# Explain clearly:
# 1. Why the user is eligible or not
# 2. Which conditions passed or failed
# 3. What could be changed to become eligible (if applicable)
# """

def build_explanation_prompt(scheme_name: str, evaluation: dict) -> str:
    lines = []

    for step in evaluation["trace"]:
        status = "PASSED" if step["passed"] else "FAILED"
        lines.append(
            f"- {step['description']} → {status} (actual={step['actual']})"
        )

    trace_text = "\n".join(lines)

    return f"""
Explain this welfare eligibility decision.

Scheme: {scheme_name}
Decision: {"Eligible" if evaluation["eligible"] else "Not Eligible"}

Evaluation:
{trace_text}

Explain briefly why this decision was made.
"""


