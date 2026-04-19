import sys
from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..config import get_settings
from ..models import OptionsResponse
from ..settings_store import get_active_constellation_presets

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
    return OptionsResponse(
        comms_payloads=list(c.COMMS_PAYLOADS.keys()),
        weather_scenarios=list(c.WEATHER_SCENARIOS.keys()),
        locations=list(c.LOCATIONS.keys()),
        sea_routes=list(c.SEA_ROUTES.keys()),
        arctic_routes=list(c.ARCTIC_ROUTES.keys()),
        platforms=list(c.TCO_CONFIG["satellite_platforms"].keys()),
        backends=c.AVAILABLE_BACKENDS,
        constellation_presets=presets,
    )
