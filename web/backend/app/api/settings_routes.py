"""
settings_routes.py — GET/PUT /api/settings
"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..config import Settings, get_settings
from ..settings_store import (
    get_settings_merged,
    get_active_constellation_presets,
    load_overrides,
    save_overrides,
    reset_comms_tech,
    reset_section,
    reset_route,
    save_constellation_preset,
    delete_constellation_preset,
    get_active_multi_shell_groups,
    save_multi_shell_group,
    delete_multi_shell_group,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_sim_settings(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return current simulation constants (defaults deep-merged with user overrides)."""
    try:
        return get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {e}")


@router.put("")
async def update_sim_settings(
    body: dict,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Save simulation constant overrides. Body must match the structure:
      { "comms_payloads": { "vdes": { "req_snr_dl": 14.0 } },
        "weather_scenarios": { "rain": 6.0 } }
    Only the keys provided are stored; omitted keys keep their current override.
    """
    try:
        overrides = load_overrides(app_settings.outputs_dir)
        # Deep-merge the incoming body into stored overrides
        from ..settings_store import _deep_merge
        _deep_merge(overrides, body)
        save_overrides(app_settings.outputs_dir, overrides)
        return get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")


@router.delete("/comms/{tech}")
async def reset_comms_technology(
    tech: str,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Reset a single comms technology to its Python default."""
    reset_comms_tech(app_settings.outputs_dir, tech)
    return get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)


@router.delete("/weather")
async def reset_weather(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Reset all weather scenarios to Python defaults."""
    reset_section(app_settings.outputs_dir, "weather_scenarios")
    return get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)


# ── Route endpoints ───────────────────────────────────────────────────────────

_VALID_ROUTE_CATEGORIES = {"sea_routes", "arctic_routes"}


@router.get("/routes")
async def get_routes(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return merged sea and arctic routes."""
    merged = get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    return {"sea_routes": merged["sea_routes"], "arctic_routes": merged["arctic_routes"]}


@router.put("/routes/{category}/{name}")
async def update_route(
    category: str,
    name: str,
    body: list,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Save waypoint overrides for a single route.
    Body: [[waypoint_name, lat, lon], ...]
    """
    if category not in _VALID_ROUTE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category '{category}'. Must be one of {_VALID_ROUTE_CATEGORIES}")
    overrides = load_overrides(app_settings.outputs_dir)
    overrides.setdefault(category, {})[name] = body
    save_overrides(app_settings.outputs_dir, overrides)
    merged = get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    return {"sea_routes": merged["sea_routes"], "arctic_routes": merged["arctic_routes"]}


@router.delete("/routes/{category}/{name}")
async def reset_route_endpoint(
    category: str,
    name: str,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Reset a single route to its Python default."""
    if category not in _VALID_ROUTE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category '{category}'. Must be one of {_VALID_ROUTE_CATEGORIES}")
    reset_route(app_settings.outputs_dir, category, name)
    merged = get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    return {"sea_routes": merged["sea_routes"], "arctic_routes": merged["arctic_routes"]}


# ── TCO endpoints ─────────────────────────────────────────────────────────────

@router.get("/tco")
async def get_tco(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return merged TCO business model configuration."""
    merged = get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    return merged["tco_config"]


@router.delete("/tco")
async def reset_tco(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Reset all TCO configuration to Python defaults."""
    reset_section(app_settings.outputs_dir, "tco_config")
    merged = get_settings_merged(app_settings.simulator_root, app_settings.outputs_dir)
    return merged["tco_config"]


# ── Constellation preset endpoints ────────────────────────────────────────────

@router.get("/constellations")
async def get_constellations(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return all active (non-deleted) constellation presets."""
    return get_active_constellation_presets(app_settings.simulator_root, app_settings.outputs_dir)


@router.post("/constellations")
async def create_constellation(
    body: dict,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Add or update a constellation preset.
    Body: {"name": str, "sats": int, "planes": int, "altitude": float,
           "inclination": float, "phasing": int, "sso": bool, "description": str}
    """
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Preset name is required")
    preset = {k: v for k, v in body.items() if k != "name"}
    preset.pop("deleted", None)  # never allow setting deleted via this endpoint
    save_constellation_preset(app_settings.outputs_dir, name, preset)
    return get_active_constellation_presets(app_settings.simulator_root, app_settings.outputs_dir)


@router.delete("/constellations/{name:path}")
async def remove_constellation(
    name: str,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Delete or hide a constellation preset by name."""
    delete_constellation_preset(app_settings.outputs_dir, name)
    return get_active_constellation_presets(app_settings.simulator_root, app_settings.outputs_dir)


@router.delete("/constellations")
async def reset_constellations(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Reset all constellation presets to Python defaults."""
    reset_section(app_settings.outputs_dir, "constellation_presets")
    return get_active_constellation_presets(app_settings.simulator_root, app_settings.outputs_dir)


# ── Multi-shell group endpoints ────────────────────────────────────────────

@router.get("/multi-shells")
async def get_multi_shells(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return all active multi-shell groups (built-ins + user-created)."""
    return get_active_multi_shell_groups(app_settings.simulator_root, app_settings.outputs_dir)


@router.post("/multi-shells")
async def create_multi_shell(
    body: dict,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Create or update a multi-shell group.
    Body: {"name": str, "shells": [{sats, planes, inclination, altitude_km, phasing, name?}, ...], "description": str}
    """
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")
    shells = body.get("shells", [])
    if not shells or not isinstance(shells, list):
        raise HTTPException(status_code=400, detail="At least one shell is required")
    description = body.get("description", "")
    save_multi_shell_group(app_settings.outputs_dir, name, shells, description)
    return get_active_multi_shell_groups(app_settings.simulator_root, app_settings.outputs_dir)


@router.delete("/multi-shells/{name:path}")
async def remove_multi_shell(
    name: str,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Delete or hide a multi-shell group by name."""
    delete_multi_shell_group(app_settings.outputs_dir, name)
    return get_active_multi_shell_groups(app_settings.simulator_root, app_settings.outputs_dir)


@router.put("/multi-shells/{name:path}")
async def update_multi_shell(
    name: str,
    body: dict,
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Update an existing multi-shell group (built-in or user-created).
    Updates are stored as user overrides — built-ins remain shippable via reset.
    Body: {"shells": [...], "description": str, "name": optional rename target}
    """
    new_name = (body.get("name") or name).strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Group name is required")
    shells = body.get("shells", [])
    if not shells or not isinstance(shells, list):
        raise HTTPException(status_code=400, detail="At least one shell is required")
    description = body.get("description", "")
    # If renaming, drop the old override (built-in or user) first
    if new_name != name:
        try:
            delete_multi_shell_group(app_settings.outputs_dir, name)
        except Exception:
            pass
    save_multi_shell_group(app_settings.outputs_dir, new_name, shells, description)
    return get_active_multi_shell_groups(app_settings.simulator_root, app_settings.outputs_dir)


@router.delete("/multi-shells")
async def reset_multi_shells(
    app_settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Remove all user-created multi-shell overrides (restores built-ins)."""
    reset_section(app_settings.outputs_dir, "multi_shell_groups")
    return get_active_multi_shell_groups(app_settings.simulator_root, app_settings.outputs_dir)
