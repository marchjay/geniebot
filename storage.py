from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


SETTINGS_PATH = Path(".geniebot.json")


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to write settings: {e}")


def load_settings() -> Dict[str, Any]:
    return _read_json(SETTINGS_PATH)


def save_settings(data: Dict[str, Any]) -> None:
    _write_json(SETTINGS_PATH, data)


def get_genie_channel_id() -> Optional[int]:
    data = load_settings()
    val = data.get("genie_channel_id")
    return int(val) if isinstance(val, int) or (isinstance(val, str) and val.isdigit()) else None


def set_genie_channel_id(channel_id: int) -> None:
    data = load_settings()
    data["genie_channel_id"] = int(channel_id)
    save_settings(data)
