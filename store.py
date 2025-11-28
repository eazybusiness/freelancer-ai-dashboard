import json
from pathlib import Path
from typing import Any, Dict

SEEN_PATH = Path(__file__).resolve().parent / "data" / "seen_projects.json"


def load_seen() -> Dict[str, Any]:
    if not SEEN_PATH.exists():
        return {}
    try:
        with SEEN_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def save_seen(seen: Dict[str, Any]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SEEN_PATH.open("w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)
