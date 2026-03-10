def evaluate_condition(actual, operator, expected):
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


def evaluate_scheme(user_profile: dict, scheme: dict) -> dict:
    trace = []

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

        if not passed:
            return {
                "eligible": False,
                "trace": trace
            }

    return {
        "eligible": True,
        "trace": trace
    }
