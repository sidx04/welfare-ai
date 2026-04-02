import json
import os

SCHEME_DIR = "schemes"


def load_scheme(scheme_id: str) -> dict:
    path = os.path.join(SCHEME_DIR, f"{scheme_id}.json")
    with open(path, "r") as f:
        return json.load(f)


def list_scheme_ids() -> list[str]:
    """Return all available scheme IDs from the schemes directory."""
    if not os.path.isdir(SCHEME_DIR):
        return []

    scheme_ids = []
    for filename in os.listdir(SCHEME_DIR):
        if filename.endswith(".json"):
            scheme_ids.append(filename[:-5])

    return sorted(scheme_ids)
