"""
settings_store.py — reads & writes user-overridden physics constants, route waypoints, and TCO business model.

Override file location: {outputs_dir}/settings.json
Structure:
{
  "comms_payloads":    { "vdes": { "req_snr_dl": 14.0, ... }, ... },
  "weather_scenarios": { "rain": 6.0, ... },
  "sea_routes":        { "titan_corridor": [["wp1", 49.9, -6.5], ...] },
  "arctic_routes":     { "borealis_run":   [["wp1", 71.0, 40.0], ...] },
  "tco_config":        { "satellite_platforms": { "nanosat": { "unit_cost": 0.7 } }, ... },
  "constellation_presets": { "My LEO": { "sats": 12, "planes": 3, ... } }
}
Only the keys that differ from the Python defaults need to be stored.
Note: to delete a built-in preset, set {"deleted": true} in its override entry.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


_SETTINGS_FILE = "settings.json"


def _load_python_defaults(simulator_root: Path) -> dict:
    """Import constants from the simulator package and return the raw dicts."""
    sim_path = str(simulator_root)
    if sim_path not in sys.path:
        sys.path.insert(0, sim_path)
    import importlib
    c = importlib.import_module("sim.constants")
    return {
        "comms_payloads":    copy.deepcopy(c.COMMS_PAYLOADS),
        "weather_scenarios": copy.deepcopy(c.WEATHER_SCENARIOS),
        "sea_routes":        _routes_to_api(copy.deepcopy(c.SEA_ROUTES)),
        "arctic_routes":     _routes_to_api(copy.deepcopy(c.ARCTIC_ROUTES)),
        "tco_config":        copy.deepcopy(c.TCO_CONFIG),
        "constellation_presets": copy.deepcopy(c.CONSTELLATION_PRESETS),
    }


def _routes_to_api(routes: dict) -> dict:
    """
    Convert from Python tuple format to JSON-friendly list format.
      Python: { "titan_corridor": [("wp1", lat, lon), ...] }
      API:    { "titan_corridor": [["wp1", lat, lon], ...] }
    """
    return {
        name: [[wp[0], wp[1], wp[2]] for wp in waypoints]
        for name, waypoints in routes.items()
    }


def _routes_from_api(routes: dict) -> dict:
    """Inverse of _routes_to_api — list → tuple for writing back to override."""
    return {
        name: [(wp[0], wp[1], wp[2]) for wp in waypoints]
        for name, waypoints in routes.items()
    }


def _settings_path(outputs_dir: Path) -> Path:
    return outputs_dir / _SETTINGS_FILE


def load_overrides(outputs_dir: Path) -> dict:
    """Return the raw override dict (may be empty)."""
    path = _settings_path(outputs_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_settings_merged(simulator_root: Path, outputs_dir: Path) -> dict:
    """Return defaults deep-merged with user overrides."""
    merged = _load_python_defaults(simulator_root)
    overrides = load_overrides(outputs_dir)
    _deep_merge(merged, overrides)
    return merged


def save_overrides(outputs_dir: Path, new_overrides: dict) -> None:
    """Persist new_overrides to settings.json (replaces the file entirely)."""
    outputs_dir.mkdir(parents=True, exist_ok=True)
    _settings_path(outputs_dir).write_text(
        json.dumps(new_overrides, indent=2), encoding="utf-8"
    )


def reset_section(outputs_dir: Path, section: str) -> None:
    """Remove a section (e.g. 'comms_payloads') from the overrides file."""
    overrides = load_overrides(outputs_dir)
    overrides.pop(section, None)
    save_overrides(outputs_dir, overrides)


def reset_comms_tech(outputs_dir: Path, tech: str) -> None:
    """Remove a single technology key from the comms_payloads overrides."""
    overrides = load_overrides(outputs_dir)
    overrides.setdefault("comms_payloads", {}).pop(tech, None)
    if not overrides.get("comms_payloads"):
        overrides.pop("comms_payloads", None)
    save_overrides(outputs_dir, overrides)


def reset_route(outputs_dir: Path, category: str, name: str) -> None:
    """Remove a single route override (category = 'sea_routes' | 'arctic_routes')."""
    overrides = load_overrides(outputs_dir)
    overrides.setdefault(category, {}).pop(name, None)
    if not overrides.get(category):
        overrides.pop(category, None)
    save_overrides(outputs_dir, overrides)


def get_active_constellation_presets(simulator_root: Path, outputs_dir: Path) -> dict:
    """Return merged constellation presets, excluding any marked deleted."""
    merged = get_settings_merged(simulator_root, outputs_dir)
    return {
        name: preset
        for name, preset in merged.get("constellation_presets", {}).items()
        if not preset.get("deleted", False)
    }


def save_constellation_preset(outputs_dir: Path, name: str, preset: dict) -> None:
    """Add or update a single constellation preset in overrides."""
    overrides = load_overrides(outputs_dir)
    overrides.setdefault("constellation_presets", {})[name] = preset
    save_overrides(outputs_dir, overrides)


def delete_constellation_preset(outputs_dir: Path, name: str) -> None:
    """Mark a constellation preset as deleted in overrides."""
    overrides = load_overrides(outputs_dir)
    overrides.setdefault("constellation_presets", {})[name] = {"deleted": True}
    save_overrides(outputs_dir, overrides)


# ── Multi-shell group store ───────────────────────────────────────────────────

def get_active_multi_shell_groups(simulator_root: Path, outputs_dir: Path) -> dict:
    """
    Return merged multi-shell groups.

    Built-in groups come from sim.constants.KNOWN_CONSTELLATIONS.
    User-created/deleted groups are stored in settings.json under "multi_shell_groups".
    A group with {"deleted": True} hides the built-in entry.
    User entries without "deleted" override or extend the built-in list.
    """
    sim_path = str(simulator_root)
    if sim_path not in sys.path:
        sys.path.insert(0, sim_path)
    import importlib
    c = importlib.import_module("sim.constants")
    builtin: dict = getattr(c, "KNOWN_CONSTELLATIONS", {})

    overrides = load_overrides(outputs_dir)
    user_groups: dict = overrides.get("multi_shell_groups", {})

    merged: dict = {}
    # Start with built-ins
    for name, shells in builtin.items():
        override = user_groups.get(name, {})
        if override.get("deleted"):
            continue
        merged[name] = {"shells": shells, "description": override.get("description", ""), "builtin": True}

    # Add/override with user-created groups (non-deleted, non-builtin)
    for name, group in user_groups.items():
        if group.get("deleted"):
            continue
        if name not in merged:
            merged[name] = {"shells": group.get("shells", []), "description": group.get("description", ""), "builtin": False}

    return merged


def save_multi_shell_group(outputs_dir: Path, name: str, shells: list, description: str = "") -> None:
    """Save a user-defined multi-shell group."""
    overrides = load_overrides(outputs_dir)
    overrides.setdefault("multi_shell_groups", {})[name] = {
        "shells": shells,
        "description": description,
    }
    save_overrides(outputs_dir, overrides)


def delete_multi_shell_group(outputs_dir: Path, name: str) -> None:
    """Delete a multi-shell group (marks built-ins as deleted; removes user groups)."""
    overrides = load_overrides(outputs_dir)
    groups = overrides.setdefault("multi_shell_groups", {})

    sim_path = str(outputs_dir.parent)  # heuristic — mark deleted for any name
    # Just mark as deleted — builtin or user
    groups[name] = {"deleted": True}
    save_overrides(outputs_dir, overrides)


def _deep_merge(base: Any, override: Any) -> Any:
    """Recursively merge override into base (in-place for dicts)."""
    if isinstance(base, dict) and isinstance(override, dict):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                _deep_merge(base[k], v)
            else:
                base[k] = v
    return base
