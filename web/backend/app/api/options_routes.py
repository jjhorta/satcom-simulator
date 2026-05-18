import sys
from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..config import get_settings
from ..models import OptionsResponse, MultiShellPreset, ShellDef
from ..settings_store import get_active_constellation_presets, get_active_multi_shell_groups

router = APIRouter(prefix="/api/options", tags=["options"])


def _get_sim_constants():
    """Import sim constants from the mounted simulator package."""
    from ..config import get_settings
    import importlib
    settings = get_settings()
    if str(settings.simulator_root) not in sys.path:
        sys.path.insert(0, str(settings.simulator_root))
    return importlib.import_module("sim.constants")


@router.get("", response_model=OptionsResponse)
async def get_options(
    app_settings=Depends(get_settings),
    _: str = Depends(get_current_user),
):
    c = _get_sim_constants()
    presets = get_active_constellation_presets(app_settings.simulator_root, app_settings.outputs_dir)

    # Build known_constellations from the merged store (built-ins + user groups)
    raw_groups = get_active_multi_shell_groups(app_settings.simulator_root, app_settings.outputs_dir)
    known: dict[str, MultiShellPreset] = {}
    _SHELL_KEYS = set(ShellDef.model_fields)
    for name, group in raw_groups.items():
        shells_raw = group.get("shells", [])
        description = group.get("description") or ""
        if not description:
            total_sats = sum(s.get("sats", 0) for s in shells_raw)
            altitudes = list({s.get("altitude_km", 0) for s in shells_raw})
            num_shells = len(shells_raw)
            description = f"{num_shells} shell{'s' if num_shells > 1 else ''}, {total_sats} sats"
            if len(altitudes) == 1:
                description += f", {int(altitudes[0])} km"
        known[name] = MultiShellPreset(
            shells=[ShellDef(**{k: v for k, v in s.items() if k in _SHELL_KEYS}) for s in shells_raw],
            description=description,
        )

    return OptionsResponse(
        comms_payloads=list(c.COMMS_PAYLOADS.keys()),
        weather_scenarios=list(c.WEATHER_SCENARIOS.keys()),
        locations=list(c.LOCATIONS.keys()),
        sea_routes=list(c.SEA_ROUTES.keys()),
        arctic_routes=list(c.ARCTIC_ROUTES.keys()),
        platforms=list(c.TCO_CONFIG["satellite_platforms"].keys()),
        backends=c.AVAILABLE_BACKENDS,
        constellation_presets=presets,
        known_constellations=known,
    )
