import argparse
import json
import time
from dataclasses import dataclass, field
from statistics import mean, median
from typing import Any, Callable, Dict, List, Optional

from baseline.run_baseline import run_baseline
from llm.phi3 import Phi3LLM
from llm.prompts import build_explanation_prompt
from rule_engine import evaluate_scheme
from scheme_loader import load_scheme


@dataclass
class LatencySummary:
    component: str
    runs: int
    warmup: int
    average_ms: float
    minimum_ms: float
    maximum_ms: float
    median_ms: float
    samples_ms: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "runs": self.runs,
            "warmup": self.warmup,
            "average_ms": self.average_ms,
            "minimum_ms": self.minimum_ms,
            "maximum_ms": self.maximum_ms,
            "median_ms": self.median_ms,
            "samples_ms": self.samples_ms,
        }

    def __str__(self) -> str:
        return (
            f"{self.component}: avg={self.average_ms:.6f}ms, "
            f"min={self.minimum_ms:.6f}ms, max={self.maximum_ms:.6f}ms, "
            f"median={self.median_ms:.6f}ms over {self.runs} runs"
        )


def measure_latency(
    func: Callable[..., Any],
    *args: Any,
    runs: int = 50,
    warmup: int = 5,
    **kwargs: Any,
) -> LatencySummary:
    """Measure a callable using time.perf_counter() and return summary stats."""
    if runs <= 0:
        raise ValueError("runs must be a positive integer")
    if warmup < 0:
        raise ValueError("warmup must be zero or a positive integer")

    for _ in range(warmup):
        func(*args, **kwargs)

    samples: List[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        samples.append((end - start) * 1000)

    return LatencySummary(
        component=getattr(func, "__name__", "anonymous"),
        runs=runs,
        warmup=warmup,
        average_ms=mean(samples),
        minimum_ms=min(samples),
        maximum_ms=max(samples),
        median_ms=median(samples),
        samples_ms=samples,
    )


def measure_rule_engine_latency(
    user_profile: Dict[str, Any],
    scheme: Dict[str, Any],
    runs: int = 50,
    warmup: int = 5,
) -> LatencySummary:
    return measure_latency(
        evaluate_scheme,
        user_profile,
        scheme,
        runs=runs,
        warmup=warmup,
    )


def measure_llm_baseline_latency(
    llm: Phi3LLM,
    scheme_id: str,
    scheme_name: str,
    user_profile: Dict[str, Any],
    runs: int = 50,
    warmup: int = 3,
) -> LatencySummary:
    return measure_latency(
        run_baseline,
        llm,
        scheme_id,
        scheme_name,
        user_profile,
        runs=runs,
        warmup=warmup,
    )


def measure_proposed_system_latency(
    llm: Phi3LLM,
    scheme_name: str,
    scheme: Dict[str, Any],
    user_profile: Dict[str, Any],
    runs: int = 50,
    warmup: int = 3,
) -> LatencySummary:
    def pipeline() -> None:
        evaluation = evaluate_scheme(user_profile, scheme)
        prompt = build_explanation_prompt(scheme_name, evaluation)
        llm.generate(prompt, max_tokens=80)

    return measure_latency(pipeline, runs=runs, warmup=warmup)


def measure_all_latencies(
    llm: Phi3LLM,
    scheme_id: str,
    scheme: Dict[str, Any],
    user_profile: Dict[str, Any],
    runs: int = 50,
    warmup: int = 3,
) -> Dict[str, LatencySummary]:
    return {
        "rule_engine": measure_rule_engine_latency(user_profile, scheme, runs=runs, warmup=warmup),
        "llm_baseline": measure_llm_baseline_latency(
            llm,
            scheme_id,
            scheme["scheme_name"],
            user_profile,
            runs=runs,
            warmup=warmup,
        ),
        "proposed_system": measure_proposed_system_latency(
            llm,
            scheme["scheme_name"],
            scheme,
            user_profile,
            runs=runs,
            warmup=warmup,
        ),
    }


def default_profile() -> Dict[str, Any]:
    return {
        "age": 35,
        "income": 450000,
        "category": "SC",
        "state": "Karnataka",
        "owns_house": False,
        "owns_lpg": False,
        "land_owned_hectares": 1.5,
        "has_health_insurance": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure latency for the welfare eligibility pipelines."
    )
    parser.add_argument(
        "--scheme",
        default="pmay",
        help="Scheme ID to evaluate (default: pmay)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of timed runs per component (default: 20)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="Number of warmup runs before timing (default: 3)",
    )
    parser.add_argument(
        "--profile-file",
        help="JSON file containing a user profile dictionary",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print results as a JSON object",
    )
    return parser.parse_args()


def load_profile(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return default_profile()

    with open(path, "r", encoding="utf-8") as handle:
        profile = json.load(handle)

    if not isinstance(profile, dict):
        raise ValueError("profile-file must contain a JSON object")

    return profile


def main() -> None:
    args = parse_args()
    scheme = load_scheme(args.scheme)
    profile = load_profile(args.profile_file)

    print(f"Scheme: {args.scheme} ({scheme['scheme_name']})")
    print(f"Profile: {profile}")
    print(f"Runs: {args.runs}, Warmup: {args.warmup}\n")

    llm = Phi3LLM()
    summaries = measure_all_latencies(
        llm,
        args.scheme,
        scheme,
        profile,
        runs=args.runs,
        warmup=args.warmup,
    )

    if args.json:
        print(json.dumps({k: v.to_dict() for k, v in summaries.items()}, indent=2))
        return

    for summary in summaries.values():
        print(summary)


if __name__ == "__main__":
    main()
