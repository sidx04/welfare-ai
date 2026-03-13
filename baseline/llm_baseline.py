def build_baseline_prompt(scheme_name: str, scheme_rules: str, user_profile: dict) -> str:
    """
    Build a baseline instruction prompt for Phi-3 Mini Instruct.

    Presents the full eligibility rules and applicant details, then asks
    the model to produce a decision sentence.  The chat template and
    system role are applied inside Phi3LLM.generate().
    """
    user_text = "\n".join(
        [f"{k}: {v}" for k, v in user_profile.items()]
    )

    return (
        f"A welfare eligibility officer is reviewing an application for {scheme_name}.\n\n"
        f"Eligibility rules:\n{scheme_rules.strip()}\n\n"
        f"Applicant details:\n{user_text}\n\n"
        "Based on the rules and the applicant's details, state in one sentence "
        "whether the applicant is eligible and the primary reason."
    )