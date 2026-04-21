"""
llm/hallucination_detector.py
─────────────────────────────

Detects hallucinations in LLM explanations by comparing against rule traces.

Hallucination types detected:
  1. False Criteria     — mentions criteria not in the trace
  2. Wrong Thresholds   — correct field but wrong numeric value
  3. Inverted Logic     — gets the sense wrong (< vs >, == vs !=, etc.)
  4. Fake Benefits      — claims benefits/features not in the scheme

Implementation:
  • Extract "ground truth fingerprint" from rule trace
  • Parse LLM explanation for mentioned fields, values, descriptions
  • Cross-reference against the fingerprint to flag contradictions
  • Score hallucination severity: 0 (none) → 1 (high)
"""

import re
from typing import Dict, List, Any, Tuple, Optional


class HallucinationDetector:
    """Detects hallucinations in LLM explanations by comparing to rule traces."""

    def __init__(self):
        # Common keywords that appear in scheme explanations
        self.field_keywords = {
            "income": ["income", "earning", "salary", "annual", "earn"],
            "age": ["age", "years", "year old", "elderly"],
            "category": ["category", "caste", "schedule", "sc/st", "obc", "bpl", "general"],
            "owns_house": ["house", "pucca", "home", "housing", "property", "dwelling"],
            "owns_lpg": ["lpg", "gas", "connection", "fuel"],
            "land_owned_hectares": ["land", "hectare", "ha", "agricultural", "farming"],
            "has_health_insurance": ["insurance", "health", "medical", "coverage"],
            "state": ["state", "region", "province"],
        }

        # Keywords that indicate scheme benefits or outcomes
        self.benefit_keywords = [
            "subsidy",
            "grant",
            "cash transfer",
            "benefit",
            "credit",
            "loan",
            "support",
            "assistance",
            "pension",
            "allowance",
        ]

    def detect_hallucinations(
        self, llm_explanation: str, rule_trace: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect hallucinations in LLM explanation.

        Args:
            llm_explanation: The LLM-generated explanation text
            rule_trace: List of rule trace dicts from rule_engine_result["trace"]

        Returns:
            {
                "has_hallucinations": bool,
                "hallucination_count": int,
                "severity_score": float (0.0 to 1.0),
                "hallucinations": [
                    {
                        "type": "false_criteria" | "wrong_threshold" | "inverted_logic" | "fake_benefit",
                        "field": str or None,
                        "description": str,
                        "expected": str,
                        "actual_in_explanation": str,
                    }
                ],
            }
        """
        hallucinations = []

        # Build ground truth fingerprint from trace
        gt_fields = self._extract_gt_fields(rule_trace)
        gt_thresholds = self._extract_gt_thresholds(rule_trace)
        gt_descriptions = self._extract_gt_descriptions(rule_trace)

        # Parse the explanation
        mentioned_fields = self._extract_mentioned_fields(llm_explanation)
        mentioned_thresholds = self._extract_mentioned_thresholds(llm_explanation)
        explanation_lower = llm_explanation.lower()

        # Check 1: False Criteria (mentions a field not in trace)
        for field in mentioned_fields:
            if field not in gt_fields:
                hallucinations.append(
                    {
                        "type": "false_criteria",
                        "field": field,
                        "description": f"Mentions criterion '{field}' not in rule trace",
                        "expected": f"Not mentioned in criteria",
                        "actual_in_explanation": f"Found reference to '{field}'",
                    }
                )

        # Check 2: Wrong Thresholds (mentions correct field but wrong value)
        for field, values in mentioned_thresholds.items():
            if field in gt_thresholds:
                expected_values = gt_thresholds[field]
                for mentioned_val in values:
                    if mentioned_val not in expected_values:
                        # Find which expected thresholds apply
                        expected_str = ", ".join(str(v) for v in expected_values)
                        hallucinations.append(
                            {
                                "type": "wrong_threshold",
                                "field": field,
                                "description": f"Incorrect threshold mentioned for '{field}'",
                                "expected": expected_str,
                                "actual_in_explanation": str(mentioned_val),
                            }
                        )

        # Check 3: Inverted Logic (says "must own" when rule says "must not own")
        for rule in rule_trace:
            field = rule["field"]
            operator = rule["operator"]
            description = rule["description"].lower()

            # Look for contradictions in the explanation text
            if field == "owns_house" and operator == "==":
                if rule["required"] is False:  # Must NOT own
                    if any(phrase in explanation_lower for phrase in ["must own", "must have", "requires house"]):
                        hallucinations.append(
                            {
                                "type": "inverted_logic",
                                "field": field,
                                "description": "Incorrectly states requirement to own a house (opposite of rule)",
                                "expected": "Applicant must NOT own a pucca house",
                                "actual_in_explanation": "Suggests ownership is required",
                            }
                        )

            if field == "owns_lpg" and operator == "==":
                if rule["required"] is False:  # Must NOT own
                    if any(phrase in explanation_lower for phrase in ["must have lpg", "must own gas", "requires lpg"]):
                        hallucinations.append(
                            {
                                "type": "inverted_logic",
                                "field": field,
                                "description": "Incorrectly states requirement to have LPG (opposite of rule)",
                                "expected": "Applicant must NOT have an existing LPG connection",
                                "actual_in_explanation": "Suggests LPG ownership is required",
                            }
                        )

        # Check 4: Fake Benefits (mentions benefits not in the scheme)
        fake_benefits = self._detect_fake_benefits(llm_explanation, rule_trace)
        hallucinations.extend(fake_benefits)

        # Compute severity score: 0.0 (no hallucinations) to 1.0 (many/severe)
        severity_score = self._compute_severity(hallucinations)

        return {
            "has_hallucinations": len(hallucinations) > 0,
            "hallucination_count": len(hallucinations),
            "severity_score": severity_score,
            "hallucinations": hallucinations,
        }

    def _extract_gt_fields(self, rule_trace: List[Dict[str, Any]]) -> set:
        """Extract all fields mentioned in the rule trace."""
        return {rule["field"] for rule in rule_trace}

    def _extract_gt_thresholds(self, rule_trace: List[Dict[str, Any]]) -> Dict[str, List]:
        """Extract expected thresholds from rule trace."""
        thresholds = {}
        for rule in rule_trace:
            field = rule["field"]
            required = rule["required"]
            if isinstance(required, (int, float)):
                if field not in thresholds:
                    thresholds[field] = []
                thresholds[field].append(required)
            elif isinstance(required, list):
                if field not in thresholds:
                    thresholds[field] = []
                thresholds[field].extend(required)
        return thresholds

    def _extract_gt_descriptions(self, rule_trace: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extract ground truth descriptions."""
        return {rule["field"]: rule["description"] for rule in rule_trace}

    def _extract_mentioned_fields(self, explanation: str) -> set:
        """Extract field names mentioned in the explanation."""
        mentioned = set()
        explanation_lower = explanation.lower()

        for field, keywords in self.field_keywords.items():
            for kw in keywords:
                if kw in explanation_lower:
                    mentioned.add(field)
                    break

        return mentioned

    def _extract_mentioned_thresholds(self, explanation: str) -> Dict[str, List]:
        """
        Extract numeric thresholds mentioned in the explanation.
        Returns dict mapping field -> list of mentioned values.
        """
        thresholds = {}

        # Find all numbers in the explanation
        numbers = re.findall(r"\d+(?:,\d+)*(?:\.\d+)?", explanation)
        numbers = [float(n.replace(",", "")) for n in numbers]

        # Associate numbers with fields if they appear nearby
        explanation_lower = explanation.lower()

        # Income patterns
        if "income" in explanation_lower or "earning" in explanation_lower:
            thresholds["income"] = numbers

        # Age patterns
        if any(kw in explanation_lower for kw in ["age", "years", "year old"]):
            age_numbers = [n for n in numbers if 0 <= n <= 120]
            if age_numbers:
                thresholds["age"] = age_numbers

        # Land patterns
        if any(kw in explanation_lower for kw in ["land", "hectare", "ha"]):
            land_numbers = [n for n in numbers if n <= 100]
            if land_numbers:
                thresholds["land_owned_hectares"] = land_numbers

        return thresholds

    def _detect_fake_benefits(
        self, explanation: str, rule_trace: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect mentions of benefits/features not in the scheme."""
        fake_benefits = []
        explanation_lower = explanation.lower()

        # Suspicious benefit mentions (that aren't typical eligibility criteria)
        suspicious_phrases = {
            "free housing": "Housing is provided by schemes, but this is eligibility criteria only",
            "monthly stipend": "No cash stipend mentioned in eligibility",
            "land grant": "Land grants not part of these schemes",
            "job guarantee": "Employment guarantees not mentioned",
            "education subsidy": "Education benefits not part of welfare schemes",
        }

        for phrase, reason in suspicious_phrases.items():
            if phrase in explanation_lower:
                fake_benefits.append(
                    {
                        "type": "fake_benefit",
                        "field": None,
                        "description": reason,
                        "expected": "No mention in rule trace",
                        "actual_in_explanation": phrase,
                    }
                )

        return fake_benefits

    def _compute_severity(self, hallucinations: List[Dict[str, Any]]) -> float:
        """Compute a severity score from 0.0 to 1.0."""
        if not hallucinations:
            return 0.0

        # Assign weights by type
        weights = {
            "false_criteria": 0.4,
            "wrong_threshold": 0.3,
            "inverted_logic": 0.5,  # More severe
            "fake_benefit": 0.4,
        }

        total_weight = sum(weights.get(h["type"], 0.2) for h in hallucinations)

        # Normalize: assume max ~3 high-severity hallucinations = 1.0
        max_expected_weight = 1.5
        return min(total_weight / max_expected_weight, 1.0)


def detect_hallucination_rate(
    experiments: List[Dict[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute hallucination rate across a batch of experiments.

    Args:
        experiments: List of experiment dicts (from JSONL)

    Returns:
        (hallucination_rate: float 0.0-1.0, stats: dict with per-scheme breakdowns)
    """
    detector = HallucinationDetector()

    total = 0
    hallucinated = 0
    per_scheme = {}

    for exp in experiments:
        scheme_name = exp.get("scheme_name", "unknown")
        explanation = exp.get("proposed_system_explanation", "")
        trace = exp.get("rule_engine_result", {}).get("trace", [])

        result = detector.detect_hallucinations(explanation, trace)

        total += 1
        if result["has_hallucinations"]:
            hallucinated += 1

        if scheme_name not in per_scheme:
            per_scheme[scheme_name] = {"total": 0, "hallucinated": 0, "severity_sum": 0.0}

        per_scheme[scheme_name]["total"] += 1
        if result["has_hallucinations"]:
            per_scheme[scheme_name]["hallucinated"] += 1
        per_scheme[scheme_name]["severity_sum"] += result["severity_score"]

    # Compute per-scheme rates
    per_scheme_rates = {}
    for scheme_name, data in per_scheme.items():
        rate = data["hallucinated"] / data["total"] if data["total"] > 0 else 0.0
        avg_severity = data["severity_sum"] / data["total"] if data["total"] > 0 else 0.0
        per_scheme_rates[scheme_name] = {
            "hallucination_rate": rate,
            "avg_severity": avg_severity,
            "total_experiments": data["total"],
            "hallucinated_count": data["hallucinated"],
        }

    overall_rate = hallucinated / total if total > 0 else 0.0

    return overall_rate, per_scheme_rates
