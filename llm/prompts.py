def format_explanation_block(scheme_name: str, evaluation: dict) -> str:
    """
    Deterministically format the structured explanation block from the
    rule engine's evaluation result. No LLM involved here.
    """
    decision = "Not Eligible" if not evaluation["eligible"] else "Eligible"

    lines = []
    lines.append(f"Scheme: {scheme_name}")
    lines.append(f"Decision: {decision}")
    lines.append("")
    lines.append("Evaluation:")

    for step in evaluation["trace"]:
        status = "PASSED" if step["passed"] else "FAILED"
        lines.append(f"  - {step['description']} -> {status} (actual={step['actual']})")

    return "\n".join(lines)


def build_explanation_prompt(scheme_name: str, evaluation: dict) -> str:
    """
    Build an instruction prompt for Phi-3 Mini Instruct.

    The structured block provides deterministic context; the model is
    asked to produce a clear, concise explanation anchored in rule-engine
    failure/passage details.
    """
    structured_block = format_explanation_block(scheme_name, evaluation)

    # Ensure the LLM is explicitly grounded in rule-engine reasoning
    failed_reasons = evaluation.get("failed_reasons", [])
    passed_reasons = []
    if not failed_reasons and evaluation.get("status") == "eligible":
        passed_reasons = [step["description"] for step in evaluation.get("trace", []) if step.get("passed")]

    detail_section = ""
    if failed_reasons:
        detail_section = ("\n\nRule engine detected failures:\n" +
                          "\n".join(f"- {reason}" for reason in failed_reasons) +
                          "\n\n")
    elif passed_reasons:
        detail_section = ("\n\nRule engine verified key passing conditions:\n" +
                          "\n".join(f"- {reason}" for reason in passed_reasons[:3]) +
                          "\n\n")

    return (
        f"{structured_block}{detail_section}\n"
        "Using the above information, write 2-3 sentences that clearly state the final eligibility decision, "
        "the main reason(s) (including the specific condition line if not eligible), and a recommended next step. "
        "The explanation should be factual, grounded in those rule-engine points, and user-friendly (about 40-70 words)."
    )