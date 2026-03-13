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
    asked to produce a single plain-English summary sentence.  Phi-3 is
    an instruction-tuned model — the chat template and system role are
    applied inside Phi3LLM.generate(), so this function just returns the
    user-facing task description.
    """
    structured_block = format_explanation_block(scheme_name, evaluation)

    return (
        f"{structured_block}\n\n"
        "In one sentence, explain whether the applicant is eligible and the "
        "main reason why or why not."
    )