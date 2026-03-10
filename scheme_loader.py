import json
import os

SCHEME_DIR = "schemes"

def load_scheme(scheme_id: str) -> dict:
    path = os.path.join(SCHEME_DIR, f"{scheme_id}.json")
    with open(path, "r") as f:
        return json.load(f)
