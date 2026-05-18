"""
ai_config_store.py — server-side storage for AI/LLM configuration.

The API key is stored ONLY on the server (outputs_dir/ai_config.json).
It is NEVER returned to the browser — only a masked representation and
a boolean `key_is_set` are exposed.

Priority: file storage > environment variables (AI_API_KEY, AI_BASE_URL, AI_MODEL)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG_FILE = "ai_config.json"
_DEFAULT_MODEL = "gpt-4o"
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_SYSTEM_PROMPT = (
    "You are an expert satellite communications and constellation engineering analyst. "
    "Analyse the provided simulation data and give concise, actionable engineering insights. "
    "Focus on coverage gaps, link budget margins, revisit time implications, and cost efficiency. "
    "Use metric units. Be direct and technical."
)


def _config_path(outputs_dir: Path) -> Path:
    return outputs_dir / _CONFIG_FILE


def load_config(outputs_dir: Path) -> dict:
    """
    Return the full AI config dict including the raw API key.
    For internal use only — never pass this dict directly to API responses.
    """
    stored: dict = {}
    path = _config_path(outputs_dir)
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            stored = {}

    # Env-var fallbacks (file takes priority)
    return {
        "api_key":       stored.get("api_key")   or os.environ.get("AI_API_KEY", ""),
        "base_url":      stored.get("base_url")  or os.environ.get("AI_BASE_URL", _DEFAULT_BASE_URL),
        "model":         stored.get("model")     or os.environ.get("AI_MODEL",    _DEFAULT_MODEL),
        "system_prompt": stored.get("system_prompt", _DEFAULT_SYSTEM_PROMPT),
    }


def save_config(outputs_dir: Path, patch: dict) -> None:
    """
    Persist AI config. Pass only the fields to update.
    If 'api_key' is an empty string it is ignored (keeps existing key).
    """
    path = _config_path(outputs_dir)
    current: dict = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            current = {}

    for field in ("base_url", "model", "system_prompt"):
        if field in patch and patch[field] is not None:
            current[field] = patch[field]

    # Only overwrite key if a non-empty value was provided
    if patch.get("api_key"):
        current["api_key"] = patch["api_key"]

    outputs_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")


def public_status(outputs_dir: Path) -> dict:
    """
    Return a safe representation for the browser:
      { key_is_set, masked_key, base_url, model, system_prompt }
    The raw API key is NEVER included.
    """
    cfg = load_config(outputs_dir)
    key = cfg["api_key"]
    if key and len(key) >= 8:
        masked = "****" + key[-4:]
    elif key:
        masked = "****"
    else:
        masked = ""
    return {
        "key_is_set":    bool(key),
        "masked_key":    masked,
        "base_url":      cfg["base_url"],
        "model":         cfg["model"],
        "system_prompt": cfg["system_prompt"],
    }


def feature_gate(outputs_dir: Path) -> dict | None:
    """
    Returns config dict if the key is set, None otherwise.
    All LLM routes must call this and abort(400) if None.
    """
    cfg = load_config(outputs_dir)
    if not cfg["api_key"]:
        return None
    return cfg
