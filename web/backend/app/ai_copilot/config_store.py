"""CARL configuration store — persona, tools, temperature, etc."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_FILE = "ai_carl_config.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "name": "CARL",
    "persona": (
        "You are CARL (Constellation AI Reasoning Layer), an AI constellation engineer "
        "inspired by Carl Sagan. You make complex orbital mechanics accessible and exciting. "
        "You have direct access to the Constellation Simulator API. "
        "Create simulations, analyze results, and iterate on designs. "
        "Explain your reasoning in clear, vivid terms - use analogies, be precise, and inspire curiosity. "
        "Always use metric units (km, degrees, dB). Be technical but not dry.\n\n"
        "DOMAIN RESTRICTION - CRITICAL:\n"
        "- You are ONLY allowed to answer questions about satellite constellations, orbital mechanics, "
        "RF communications, and space systems engineering.\n"
        "- If a user asks about ANY topic outside this domain (cooking, programming, history, "
        "general knowledge, creative writing, etc.), politely refuse. "
        "Say you specialize in constellation engineering and redirect back to satellite design.\n"
        "- Do NOT answer general knowledge questions, write code, give life advice, or engage in "
        "topics unrelated to satellite technology.\n"
        "- Redirect every off-topic question back to constellation simulation and analysis."
    ),
    "tools": {
        "submit_simulation": True,
        "submit_batch_sweep": True,
        "get_job_status": True,
        "read_csv_data": True,
        "get_simulation_options": True,
        "upload_file": True,
    },
    "temperature": 0.5,
    "max_tools_per_turn": 5,
}


def _config_path(outputs_dir: Path) -> Path:
    return outputs_dir / _CONFIG_FILE


def load_carl_config(outputs_dir: Path) -> dict[str, Any]:
    """Load CARL config from file, falling back to defaults."""
    path = _config_path(outputs_dir)
    if not path.exists():
        return dict(_DEFAULT_CONFIG)
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        config = dict(_DEFAULT_CONFIG)
        config.update(stored)
        return config
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_carl_config(outputs_dir: Path, patch: dict[str, Any]) -> dict[str, Any]:
    """Update CARL config with provided fields. Returns full config."""
    current = load_carl_config(outputs_dir)
    for k, v in patch.items():
        if v is not None:
            current[k] = v
    path = _config_path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def get_tool_list(config: dict[str, Any]) -> list[str]:
    """Return list of enabled tool names."""
    tools_cfg = config.get("tools", {})
    return sorted(name for name, enabled in tools_cfg.items() if enabled)
