"""
llm/what_if_engine.py
──────────────────────

Generates counterfactual "What-If" scenarios to help users understand
how to become eligible for schemes they currently don't qualify for.

Key features:
  • Identifies failed conditions from rule trace
  • Generates minimal changes needed to pass each condition
  • Computes feasibility scores for each scenario
  • Ranked by ease/practicality of achieving

Example:
    "Your income exceeds PM-KISAN limit.
     If your income were ₹2.4L (currently ₹3L), you'd be eligible."
"""

from typing import Dict, List, Any, Tuple, Optional
import math


class WhatIfScenario:
    """Represents a single what-if scenario."""

    def __init__(
        self,
        field: str,
        current_value: Any,
        required_value: Any,
        operator: str,
        field_description: str,
        suggested_value: Any,
        minimal_change: Any,
        feasibility_score: float,
        rationale: str,
    ):
        self.field = field
        self.current_value = current_value
        self.required_value = required_value
        self.operator = operator
        self.field_description = field_description
        self.suggested_value = suggested_value
        self.minimal_change = minimal_change
        self.feasibility_score = feasibility_score
        self.rationale = rationale

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "field": self.field,
            "current_value": self.current_value,
            "required_value": self.required_value,
            "operator": self.operator,
            "field_description": self.field_description,
            "suggested_value": self.suggested_value,
            "minimal_change": self.minimal_change,
            "feasibility_score": round(self.feasibility_score, 2),
            "feasibility_label": self._get_feasibility_label(),
            "rationale": self.rationale,
        }

    def _get_feasibility_label(self) -> str:
        """Return human-readable feasibility label."""
        if self.feasibility_score >= 0.8:
            return "🟢 Highly Feasible"
        elif self.feasibility_score >= 0.5:
            return "🟡 Moderately Feasible"
        else:
            return "🔴 Difficult"


class WhatIfEngine:
    """
    Generates counterfactual scenarios to show users how to become eligible.
    """

    # Feasibility weights for different field types
    FEASIBILITY_WEIGHTS = {
        "income": 0.4,  # Hard to change, but possible
        "age": 0.1,  # Very hard (cannot go backwards)
        "owns_house": 0.6,  # Moderate (can sell)
        "owns_lpg": 0.7,  # Easy (can acquire/connect)
        "land_owned_hectares": 0.3,  # Hard (requires land purchase)
        "category": 0.05,  # Essentially impossible
        "has_health_insurance": 0.8,  # Easy (can enroll)
        "state": 0.0,  # Impossible without relocation
    }

    def generate_scenarios(
        self, profile: Dict[str, Any], rule_trace: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate what-if scenarios for all failed conditions.

        Args:
            profile: User profile dict
            rule_trace: List of rule trace items from rule_engine_result["trace"]

        Returns:
            List of scenario dicts, ranked by feasibility (highest first)
        """
        scenarios = []

        # Filter to only failed conditions
        failed_conditions = [r for r in rule_trace if not r["passed"]]

        for condition in failed_conditions:
            field = condition["field"]
            operator = condition["operator"]
            required = condition["required"]
            actual = condition["actual"]
            description = condition["description"]

            scenario = self._generate_scenario_for_field(
                field, operator, required, actual, description
            )

            if scenario:
                scenarios.append(scenario)

        # Sort by feasibility (highest first), then by change magnitude
        scenarios.sort(
            key=lambda s: (-s["feasibility_score"], abs(s["minimal_change"]))
        )

        return scenarios

    def _generate_scenario_for_field(
        self,
        field: str,
        operator: str,
        required: Any,
        actual: Any,
        description: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate a scenario for a single failed field."""

        if operator == "<=":
            return self._scenario_less_than_or_equal(
                field, required, actual, description
            )
        elif operator == ">=":
            return self._scenario_greater_than_or_equal(
                field, required, actual, description
            )
        elif operator == "==":
            return self._scenario_equality(field, required, actual, description)
        elif operator == "in":
            return self._scenario_in_list(field, required, actual, description)
        elif operator == ">":
            return self._scenario_greater_than(field, required, actual, description)
        elif operator == "<":
            return self._scenario_less_than(field, required, actual, description)

        return None

    def _scenario_less_than_or_equal(
        self, field: str, required: Any, actual: Any, description: str
    ) -> Dict[str, Any]:
        """Handle: actual must be <= required."""
        if isinstance(required, (int, float)) and isinstance(actual, (int, float)):
            change = actual - required
            suggested = required
            epsilon = self._get_epsilon(field, required)
            suggested_with_buffer = required - epsilon

            return WhatIfScenario(
                field=field,
                current_value=actual,
                required_value=required,
                operator="<=",
                field_description=description,
                suggested_value=suggested_with_buffer,
                minimal_change=change,
                feasibility_score=self.FEASIBILITY_WEIGHTS.get(field, 0.3),
                rationale=self._get_rationale_decrease(
                    field, actual, suggested_with_buffer, required
                ),
            ).to_dict()

        return None

    def _scenario_greater_than_or_equal(
        self, field: str, required: Any, actual: Any, description: str
    ) -> Dict[str, Any]:
        """Handle: actual must be >= required."""
        if isinstance(required, (int, float)) and isinstance(actual, (int, float)):
            change = required - actual
            suggested = required
            epsilon = self._get_epsilon(field, required)
            suggested_with_buffer = required + epsilon

            return WhatIfScenario(
                field=field,
                current_value=actual,
                required_value=required,
                operator=">=",
                field_description=description,
                suggested_value=suggested_with_buffer,
                minimal_change=change,
                feasibility_score=self.FEASIBILITY_WEIGHTS.get(field, 0.3),
                rationale=self._get_rationale_increase(
                    field, actual, suggested_with_buffer, required
                ),
            ).to_dict()

        return None

    def _scenario_equality(
        self, field: str, required: Any, actual: Any, description: str
    ) -> Dict[str, Any]:
        """Handle: actual must == required (binary conditions)."""
        # For boolean fields (owns_house, owns_lpg, has_health_insurance)
        if isinstance(required, bool):
            feasibility = self.FEASIBILITY_WEIGHTS.get(field, 0.5)

            if required is False and actual is True:
                # Must NOT own something
                action = f"Remove/sell the {field.replace('owns_', '').replace('has_', '')}"
            else:
                # Must own/have something
                action = f"Acquire/enroll in {field.replace('owns_', '').replace('has_', '')}"

            return WhatIfScenario(
                field=field,
                current_value=actual,
                required_value=required,
                operator="==",
                field_description=description,
                suggested_value=required,
                minimal_change=1,  # Binary change
                feasibility_score=feasibility,
                rationale=action,
            ).to_dict()

        return None

    def _scenario_in_list(
        self, field: str, required: List[Any], actual: Any, description: str
    ) -> Dict[str, Any]:
        """Handle: actual must be in list (category, state, etc.)."""
        # For categorical fields like category (SC, ST, OBC, BPL, General)
        feasibility = self.FEASIBILITY_WEIGHTS.get(field, 0.1)

        if field == "category":
            # Category is basically immutable
            feasibility = 0.05
            rationale = f"Change is not practical (categories are fixed at registration)"
        else:
            # For other list-based fields
            rationale = f"Must be one of: {', '.join(str(r) for r in required)}"

        # Return first valid option as suggestion
        suggested = required[0] if required else actual

        return WhatIfScenario(
            field=field,
            current_value=actual,
            required_value=required,
            operator="in",
            field_description=description,
            suggested_value=suggested,
            minimal_change=1,
            feasibility_score=feasibility,
            rationale=rationale,
        ).to_dict()

    def _scenario_greater_than(
        self, field: str, required: Any, actual: Any, description: str
    ) -> Dict[str, Any]:
        """Handle: actual must be > required."""
        if isinstance(required, (int, float)) and isinstance(actual, (int, float)):
            change = required - actual + 1
            suggested = required + 1
            epsilon = self._get_epsilon(field, required)
            suggested_with_buffer = required + epsilon

            return WhatIfScenario(
                field=field,
                current_value=actual,
                required_value=required,
                operator=">",
                field_description=description,
                suggested_value=suggested_with_buffer,
                minimal_change=change,
                feasibility_score=self.FEASIBILITY_WEIGHTS.get(field, 0.3),
                rationale=self._get_rationale_increase(
                    field, actual, suggested_with_buffer, required
                ),
            ).to_dict()

        return None

    def _scenario_less_than(
        self, field: str, required: Any, actual: Any, description: str
    ) -> Dict[str, Any]:
        """Handle: actual must be < required."""
        if isinstance(required, (int, float)) and isinstance(actual, (int, float)):
            change = actual - required + 1
            suggested = required - 1
            epsilon = self._get_epsilon(field, required)
            suggested_with_buffer = required - epsilon

            return WhatIfScenario(
                field=field,
                current_value=actual,
                required_value=required,
                operator="<",
                field_description=description,
                suggested_value=suggested_with_buffer,
                minimal_change=change,
                feasibility_score=self.FEASIBILITY_WEIGHTS.get(field, 0.3),
                rationale=self._get_rationale_decrease(
                    field, actual, suggested_with_buffer, required
                ),
            ).to_dict()

        return None

    @staticmethod
    def _get_epsilon(field: str, threshold: float) -> float:
        """
        Get a small buffer value for the field to suggest a realistic target.
        E.g., for income of 3L, suggest 2.95L to be safe.
        """
        if field == "income":
            return max(threshold * 0.02, 5000)  # 2% or ₹5k minimum
        elif field == "land_owned_hectares":
            return 0.05  # 0.05 hectare buffer
        elif field in ["age"]:
            return 1.0  # 1 year
        else:
            return threshold * 0.1 if threshold > 0 else 0.1

    @staticmethod
    def _get_rationale_decrease(
        field: str, actual: float, suggested: float, required: float
    ) -> str:
        """Generate rationale for decreasing a value."""
        diff = actual - suggested
        pct = (diff / actual * 100) if actual != 0 else 0

        if field == "income":
            return f"Reduce income from {actual:,.0f} to {suggested:,.0f} (save ₹{diff:,.0f} or ~{pct:.1f}%)"
        elif field == "land_owned_hectares":
            return f"Reduce holdings from {actual:.2f} to {suggested:.2f} hectares"
        elif field == "age":
            return f"Not possible - age cannot decrease"
        else:
            return f"Reduce {field} from {actual} to {suggested}"

    @staticmethod
    def _get_rationale_increase(
        field: str, actual: float, suggested: float, required: float
    ) -> str:
        """Generate rationale for increasing a value."""
        diff = suggested - actual
        pct = (diff / actual * 100) if actual != 0 else 0

        if field == "income":
            return f"Increase income from {actual:,.0f} to {suggested:,.0f} (gain ₹{diff:,.0f} or ~{pct:.1f}%)"
        elif field == "land_owned_hectares":
            return f"Increase holdings from {actual:.2f} to {suggested:.2f} hectares"
        elif field == "age":
            return f"Wait until age {suggested} (currently {actual})"
        else:
            return f"Increase {field} from {actual} to {suggested}"


def generate_what_if_explanations(
    profile: Dict[str, Any], rule_trace: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convenience function to generate human-readable what-if explanations.

    Args:
        profile: User profile
        rule_trace: Rule trace from evaluation

    Returns:
        Dict with:
          - scenarios: List of what-if scenarios sorted by feasibility
          - summary: One-liner recommendation
          - multiple_paths: Whether multiple improvement paths exist
    """
    engine = WhatIfEngine()
    scenarios = engine.generate_scenarios(profile, rule_trace)

    if not scenarios:
        return {
            "scenarios": [],
            "summary": "You are already eligible for this scheme!",
            "multiple_paths": False,
        }

    # Generate summary based on top scenario
    top = scenarios[0]
    if top["feasibility_score"] >= 0.7:
        summary = (
            f"Most feasible fix: {top['field_description'].lower()} → {top['rationale']}"
        )
    elif top["feasibility_score"] >= 0.4:
        summary = (
            f"Possible improvement: {top['field_description'].lower()} → {top['rationale']}"
        )
    else:
        summary = "Significant changes would be required to become eligible."

    return {
        "scenarios": scenarios,
        "summary": summary,
        "multiple_paths": len(scenarios) > 1,
        "feasible_paths": [s for s in scenarios if s["feasibility_score"] >= 0.5],
    }
