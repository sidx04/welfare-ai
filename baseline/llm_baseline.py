def build_baseline_prompt(scheme_name: str, scheme_rules: str, user_profile: dict):

    user_text = "\n".join(
        [f"{k}: {v}" for k, v in user_profile.items()]
    )

    return f"""A welfare eligibility officer is reviewing an application for {scheme_name}.

Eligibility rules:
{scheme_rules.strip()}

Applicant details:
{user_text}

After reviewing the rules and the applicant's details, the officer wrote the following decision:
The applicant is"""