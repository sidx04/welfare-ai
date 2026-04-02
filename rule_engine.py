def evaluate_condition(actual, operator, expected):
    if actual is None:
        return False

    if operator == "<":
        return actual < expected
    elif operator == "<=":
        return actual <= expected
    elif operator == ">":
        return actual > expected
    elif operator == ">=":
        return actual >= expected
    elif operator == "==":
        return actual == expected
    elif operator == "!=":
        return actual != expected
    elif operator == "in":
        if not isinstance(expected, list):
            raise ValueError("'in' operator expects a list")
        return actual in expected
    else:
        raise ValueError(f"Unsupported operator: {operator}")


def _format_failure_reason(condition: dict, actual) -> str:
    operator = condition["operator"]
    expected = condition["value"]
    description = condition.get("description", condition["field"])
    return f"{description} (actual={actual}, required {operator} {expected})"


def evaluate_scheme(user_profile: dict, scheme: dict) -> dict:
    trace = []
    passed_count = 0
    failed_reasons = []

    for condition in scheme["conditions"]:
        field = condition["field"]
        operator = condition["operator"]
        expected = condition["value"]
        description = condition["description"]

        actual = user_profile.get(field)
        passed = evaluate_condition(actual, operator, expected)

        trace.append({
            "field": field,
            "operator": operator,
            "required": expected,
            "actual": actual,
            "passed": passed,
            "description": description
        })

        if passed:
            passed_count += 1
        else:
            failed_reasons.append(_format_failure_reason(condition, actual))

    total_conditions = len(scheme["conditions"])
    eligible = passed_count == total_conditions
    status = "eligible" if eligible else "partially eligible" if passed_count > 0 else "not eligible"

    return {
        "eligible": eligible,
        "status": status,
        "passed_count": passed_count,
        "total_conditions": total_conditions,
        "pass_ratio": passed_count / total_conditions if total_conditions else 0.0,
        "failed_reasons": failed_reasons,
        "trace": trace,
    }
