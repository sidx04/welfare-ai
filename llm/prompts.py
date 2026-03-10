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
        lines.append(f"  - {step['description']} → {status} (actual={step['actual']})")

    return "\n".join(lines)


def build_explanation_prompt(scheme_name: str, evaluation: dict) -> str:
    """
    Build a completion prompt: the structured block acts as context, and the
    incomplete final sentence is what Phi-2 will continue as natural language.
    Using an incomplete sentence ("The applicant is") instead of a complete
    instruction ("Explain why...") is critical — Phi-2 is a completion model,
    not an instruction model, so it continues text, not follows commands.
    """
    structured_block = format_explanation_block(scheme_name, evaluation)

    return f"""{structured_block}

The applicant is"""