"""
Advanced features: What-If Analysis, Gap Analysis, and Counterfactual Scenarios
"""

from typing import Dict, Any, List
import copy

from scheme_loader import load_scheme, list_scheme_ids
from rule_engine import evaluate_scheme
from llm.what_if_engine import generate_what_if_explanations


def compute_gap_distance(condition: dict, actual_value: Any) -> float:
    """
    Compute how "close" the actual value is to passing the condition.
    Returns a 0-1 score where 1 = very close, 0 = very far.
    Used to rank failed conditions by importance (closest = highest priority).
    """
    operator = condition["operator"]
    required = condition["value"]

    if actual_value is None:
        return 0.0

    if operator in ["<", "<=", ">", ">="]:
        if isinstance(required, (int, float)) and isinstance(
            actual_value, (int, float)
        ):
            if operator in ["<=", "<"]:

                if actual_value <= required:
                    return 1.0
                margin = required - actual_value

                pct = margin / (abs(required) + 1)
                return min(1.0, max(0.0, 1.0 - pct))
            else:

                if actual_value >= required:
                    return 1.0
                margin = required - actual_value
                pct = margin / (abs(required) + 1)
                return min(1.0, max(0.0, 1.0 - pct))

    if operator == "==":
        return 1.0 if actual_value == required else 0.0
    if operator == "!=":
        return 1.0 if actual_value != required else 0.0
    if operator == "in":
        return 1.0 if actual_value in required else 0.0

    return 0.0


def analyze_gaps(scheme: dict, evaluation: dict, profile: dict) -> List[Dict[str, Any]]:
    """
    Analyze failed conditions and rank by "closeness to passing".
    Returns list of failed conditions with suggestions.
    """
    gaps = []

    for step in evaluation["trace"]:
        if not step["passed"]:
            condition = next(
                (c for c in scheme["conditions"] if c["field"] == step["field"]), None
            )
            if condition:
                distance = compute_gap_distance(condition, step["actual"])
                gaps.append(
                    {
                        "field": step["field"],
                        "description": step["description"],
                        "actual": step["actual"],
                        "required": condition["value"],
                        "operator": condition["operator"],
                        "distance": distance,
                        "suggestion": format_gap_suggestion(condition, step["actual"]),
                    }
                )

    gaps.sort(key=lambda g: g["distance"], reverse=True)
    return gaps


def format_gap_suggestion(condition: dict, actual: Any) -> str:
    """Generate a human-friendly suggestion to fix a failed condition."""
    field = condition["field"]
    operator = condition["operator"]
    required = condition["value"]

    if operator == "<=":
        return f"Reduce {field} to {required} or below (currently {actual})"
    elif operator == "<":
        return f"Reduce {field} to below {required} (currently {actual})"
    elif operator == ">=":
        return f"Increase {field} to {required} or above (currently {actual})"
    elif operator == ">":
        return f"Increase {field} to above {required} (currently {actual})"
    elif operator == "==":
        return f"Change {field} to {required} (currently {actual})"
    elif operator == "!=":
        return f"Change {field} to something other than {actual}"
    elif operator == "in":
        return f"Change {field} to one of: {required} (currently {actual})"
    else:
        return f"Adjust {field} to meet the requirement"


def format_improvements(before: dict, after: dict) -> List[str]:
    """Describe what changed between before and after evaluations."""
    improvements = []

    if not before["eligible"] and after["eligible"]:
        improvements.append("✅ Now ELIGIBLE!")
    elif before["status"] != after["status"]:
        improvements.append(f"Status changed: {before['status']} → {after['status']}")

    before_failed = {step["field"] for step in before["trace"] if not step["passed"]}
    after_failed = {step["field"] for step in after["trace"] if not step["passed"]}
    newly_passed = before_failed - after_failed

    if newly_passed:
        improvements.append(
            f"Fixed {len(newly_passed)} condition(s): {', '.join(newly_passed)}"
        )

    return improvements


def evaluate_what_if(profile: dict, modifications: dict) -> Dict[str, Any]:
    """
    Evaluate user profile with modifications against all schemes.
    Returns schemes that are affected by the changes.
    """

    modified_profile = copy.deepcopy(profile)
    modified_profile.update(modifications)

    scheme_ids = list_scheme_ids()
    results = []

    for scheme_id in scheme_ids:
        scheme = load_scheme(scheme_id)

        orig_eval = evaluate_scheme(profile, scheme)
        modified_eval = evaluate_scheme(modified_profile, scheme)

        status_changed = orig_eval["status"] != modified_eval["status"]
        became_eligible = not orig_eval["eligible"] and modified_eval["eligible"]

        if status_changed or became_eligible:
            results.append(
                {
                    "scheme_id": scheme_id,
                    "scheme_name": scheme["scheme_name"],
                    "before": {
                        "eligible": orig_eval["eligible"],
                        "status": orig_eval["status"],
                        "pass_ratio": orig_eval["pass_ratio"],
                    },
                    "after": {
                        "eligible": modified_eval["eligible"],
                        "status": modified_eval["status"],
                        "pass_ratio": modified_eval["pass_ratio"],
                    },
                    "changed": status_changed,
                    "improvements": format_improvements(orig_eval, modified_eval),
                }
            )

    return {
        "modifications": modifications,
        "scenarios": results,
        "summary": f"{len(results)} scheme(s) affected by the changes",
    }


def evaluate_gap_analysis(scheme_id: str, profile: dict) -> Dict[str, Any]:
    """
    Analyze failed conditions for a scheme and rank by closeness to passing.
    """
    scheme = load_scheme(scheme_id)
    evaluation = evaluate_scheme(profile, scheme)
    gaps = analyze_gaps(scheme, evaluation, profile)

    if not gaps:
        return {
            "scheme_id": scheme_id,
            "scheme_name": scheme["scheme_name"],
            "status": "eligible",
            "message": "User is eligible! No gaps to address.",
            "gaps": [],
        }

    return {
        "scheme_id": scheme_id,
        "scheme_name": scheme["scheme_name"],
        "status": evaluation["status"],
        "failed_count": len(gaps),
        "gaps": gaps,
        "summary": f"Address {len(gaps)} condition(s) to become eligible. "
        f"Start with: {gaps[0]['description']}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NEW: COUNTERFACTUAL SCENARIOS (What-If Engine)
# ═══════════════════════════════════════════════════════════════════════════════


def evaluate_counterfactuals(scheme_id: str, profile: dict) -> Dict[str, Any]:
    """
    Generate counterfactual "what-if" scenarios showing how to become eligible.

    For each failed condition, recommends minimal changes with feasibility ranking.

    Returns:
        {
            "scheme_id": str,
            "scheme_name": str,
            "is_eligible": bool,
            "scenarios": [
                {
                    "field": str,
                    "current_value": Any,
                    "required_value": Any,
                    "suggested_value": Any,
                    "feasibility_score": 0.0-1.0,
                    "feasibility_label": "🟢 Highly Feasible" | "🟡 Moderately Feasible" | "🔴 Difficult",
                    "rationale": str,
                }
            ],
            "summary": str,
            "multiple_paths": bool,
            "feasible_paths": List[Dict],
        }
    """
    try:
        scheme = load_scheme(scheme_id)
    except Exception:
        return {"error": f"Scheme {scheme_id} not found"}

    evaluation = evaluate_scheme(profile, scheme)

    if evaluation["eligible"]:
        return {
            "scheme_id": scheme_id,
            "scheme_name": scheme["scheme_name"],
            "is_eligible": True,
            "message": "🎉 You are already eligible for this scheme!",
            "scenarios": [],
            "summary": None,
            "multiple_paths": False,
            "feasible_paths": [],
        }

    what_if_result = generate_what_if_explanations(profile, evaluation["trace"])

    return {
        "scheme_id": scheme_id,
        "scheme_name": scheme["scheme_name"],
        "is_eligible": False,
        "scenarios": what_if_result["scenarios"],
        "summary": what_if_result["summary"],
        "multiple_paths": what_if_result["multiple_paths"],
        "feasible_paths": what_if_result["feasible_paths"],
    }


def evaluate_all_counterfactuals(profile: dict) -> Dict[str, Any]:
    """
    Generate counterfactual scenarios for all schemes.
    Useful for portfolio view showing all paths to eligibility.
    """
    scheme_ids = list_scheme_ids()

    results = {
        "eligible": [],
        "have_feasible_improvements": [],
        "no_feasible_improvements": [],
    }

    for scheme_id in scheme_ids:
        cfs = evaluate_counterfactuals(scheme_id, profile)

        if cfs.get("is_eligible"):
            results["eligible"].append(
                {
                    "scheme_id": cfs["scheme_id"],
                    "scheme_name": cfs["scheme_name"],
                }
            )
        elif cfs.get("feasible_paths"):

            results["have_feasible_improvements"].append(
                {
                    "scheme_id": cfs["scheme_id"],
                    "scheme_name": cfs["scheme_name"],
                    "top_improvement": cfs["feasible_paths"][0],
                    "count_feasible": len(cfs["feasible_paths"]),
                }
            )
        else:
            results["no_feasible_improvements"].append(
                {
                    "scheme_id": cfs["scheme_id"],
                    "scheme_name": cfs["scheme_name"],
                    "summary": cfs.get("summary", "No feasible paths"),
                }
            )

    return {
        "profile": profile,
        "summary": {
            "eligible": len(results["eligible"]),
            "have_feasible_improvements": len(results["have_feasible_improvements"]),
            "no_feasible_improvements": len(results["no_feasible_improvements"]),
        },
        "results": results,
    }
