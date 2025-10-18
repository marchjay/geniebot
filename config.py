from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv

# Simplified: just load .env from the current working directory
load_dotenv()

from pathlib import Path


def _load_system_prompt_prefix() -> str:
    # The environment variable SYSTEM_PROMPT_PREFIX is authoritative for the prefix.
    # It may contain either: (A) a path to a file containing the prompt, or (B) the literal
    # prompt text. We require it to be present and do not fall back to any inline defaults.
    raw = os.getenv("SYSTEM_PROMPT_PREFIX", "").strip()
    if not raw:
        raise RuntimeError("SYSTEM_PROMPT_PREFIX must be set in the environment and non-empty")

    # Heuristic: only treat the env value as a filesystem path if it looks like one.
    # Avoid calling Path.exists() on long or multiline strings (which can raise
    # OSError on some platforms when treated as filenames).
    looks_like_path = True
    if "\n" in raw or "\0" in raw:
        looks_like_path = False
    # If the raw value is extremely long, assume it's the literal prompt text
    if len(raw) > 1024:
        looks_like_path = False

    if looks_like_path:
        p = Path(raw)
        try:
            if p.exists() and p.is_file():
                try:
                    return p.read_text(encoding="utf-8").strip()
                except Exception:
                    return raw
        except OSError:
            # If the filesystem call fails (e.g. "File name too long"), treat
            # the value as literal prompt text instead of a path.
            return raw

    # Otherwise treat the environment value as the literal prompt text
    return raw


@dataclass(frozen=True)
class Settings:
    discord_bot_token: str
    allowed_channel_ids: List[int]
    openai_api_key: str
    openai_model: str
    system_prompt_prefix: str
    thread_name_template: str

    @staticmethod
    def from_env() -> "Settings":
        token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_BOT_TOKEN is required")

        allowed_raw = os.getenv("DISCORD_ALLOWED_CHANNEL_IDS", "").strip()
        # Empty or "" means allow all
        allowed: List[int] = []
        if allowed_raw:
            allowed = [
                int(x.strip()) for x in allowed_raw.split(",") if x.strip().isdigit()
            ]

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY is required")

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        system_prefix = _load_system_prompt_prefix()
        thread_name_template = os.getenv("THREAD_NAME_TEMPLATE", "genie-{author}-{id}").strip() or "genie-{author}-{id}"

        return Settings(
            discord_bot_token=token,
            allowed_channel_ids=allowed,
            openai_api_key=openai_key,
            openai_model=model,
            system_prompt_prefix=system_prefix,
            thread_name_template=thread_name_template,
        )
