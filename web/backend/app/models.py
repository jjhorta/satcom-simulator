from __future__ import annotations
from typing import Any, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Extended fields returned on login/register — optional so existing code stays compatible
    user: Optional[dict] = None


# ── User / Org / RBAC response models ────────────────────────────────────────

RoleType = Literal["admin", "team_manager", "creator", "viewer", "demo"]


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    role: RoleType
    org_id: Optional[int] = None
    org_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None
    jobs_used_this_month: int = 0
    demo_expires_at: Optional[str] = None
    demo_jobs_remaining: Optional[int] = None


class OrgOut(BaseModel):
    id: int
    name: str
    slug: str
    owner_id: int
    max_members: int = 20
    subscription_tier: str = "free"
    created_at: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    org_name: Optional[str] = None
    role: Optional[str] = "creator"


class UpdateRoleRequest(BaseModel):
    new_role: RoleType


class InviteRequest(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    role: RoleType = "creator"



class ConstellationParams(BaseModel):
    sats: int = Field(66, ge=1, le=10000)
    planes: int = Field(6, ge=1, le=1000)
    altitude: float = Field(600.0, ge=160.0, le=42000.0)   # 160 km (VLEO) to 42000 km (super-GEO)
    phasing: int = Field(1, ge=1, le=1000)
    inclination: float = Field(87.4, ge=0.0, le=180.0)
    sso: bool = False
    backend: Literal["matplotlib", "plotly", "bokeh"] = "matplotlib"


# ── Mode-specific job requests ────────────────────────────────────────────────

class HeatmapRequest(ConstellationParams):
    mode: Literal["heatmap"] = "heatmap"
    comms: str = "vdes"
    weather: str = "clear"
    res: float = Field(5.0, ge=0.5, le=20.0)
    min_elev: float = Field(10.0, ge=0.0, le=90.0)
    bidi: bool = False
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list[dict]] = None
    max_sats: int = Field(250, ge=1, le=10000)


class HeatmapRfRequest(ConstellationParams):
    mode: Literal["heatmap-rf"] = "heatmap-rf"
    comms: str = "vdes"
    weather: str = "clear"
    res: float = Field(5.0, ge=0.5, le=20.0)
    min_elev: float = Field(10.0, ge=0.0, le=90.0)
    bidi: bool = False
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list[dict]] = None
    max_sats: int = Field(250, ge=1, le=10000)


class SkyRequest(ConstellationParams):
    mode: Literal["sky"] = "sky"
    location: str = "panama_canal"
    coverage: Optional[str] = None  # None = single location; '' | sea | arctic | both | all
    comms: str = "vdes"
    weather: str = "clear"
    bidi: bool = False
    duration: int = Field(3600, ge=60, le=604800)   # up to 7 days
    speed: int = Field(60, ge=1, le=3600)
    trails: bool = False
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list[dict]] = None
    max_sats: int = Field(250, ge=1, le=10000)

    @field_validator('coverage', mode='before')
    @classmethod
    def coerce_coverage(cls, v: object) -> Optional[str]:
        """Accept bool from legacy frontends: True → 'all', False → None."""
        if isinstance(v, bool):
            return 'all' if v else None
        return v  # type: ignore[return-value]


class OrbitRequest(ConstellationParams):
    mode: Literal["orbit"] = "orbit"
    comms: str = "vdes"
    platform: Literal["nanosat", "microsat", "smallsat", "mediumsat", "largesat"] = "smallsat"
    trails: bool = False
    map: bool = False
    beams: bool = False
    fill: bool = False
    min_elev: float = Field(10.0, ge=0.0, le=90.0)
    duration: int = Field(360, ge=10, le=10080)   # up to 7 days
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list[dict]] = None
    max_sats: int = Field(250, ge=1, le=10000)


class TrackRequest(ConstellationParams):
    mode: Literal["track"] = "track"
    duration: int = Field(3600, ge=600, le=604800)   # up to 7 days
    map: bool = True


class RouteRequest(ConstellationParams):
    mode: Literal["route"] = "route"
    route: str
    comms: str = "vdes"
    weather: str = "clear"
    bidi: bool = False
    duration: int = Field(3600, ge=60, le=604800)   # up to 7 days
    speed: int = Field(60, ge=1, le=50)   # practical max for ships ~30 kn, allow up to 50
    min_elev: float = Field(10.0, ge=0.0, le=90.0)
    trails: bool = False
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list[dict]] = None
    max_sats: int = Field(250, ge=1, le=10000)


class LatencyRequest(ConstellationParams):
    mode: Literal["latency"] = "latency"
    from_location: str = Field("33.94,-118.41")
    to_location: str = Field("38.81,-77.30")
    duration: int = Field(1440, ge=1, le=10080)
    step: int = Field(5, ge=1, le=60)
    isl_range: float = Field(5000.0, ge=100.0, le=10000.0)
    switching_delay: float = Field(1.0, ge=0.0, le=50.0)
    min_elev: float = Field(10.0, ge=0.0, le=90.0)
    no_fiber: bool = False
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list[dict]] = None
    max_sats: int = Field(250, ge=1, le=10000)


JobRequest = Union[HeatmapRequest, HeatmapRfRequest, SkyRequest, OrbitRequest, TrackRequest, RouteRequest, LatencyRequest]


# ── Job response models ───────────────────────────────────────────────────────

class JobFile(BaseModel):
    name: str
    type: Literal["csv", "png", "gif", "html", "txt", "log", "json"]
    url: str
    size_bytes: int


class JobStatus(BaseModel):
    job_id: str
    mode: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    params: dict
    files: list[JobFile] = []
    log_tail: Optional[str] = None
    error: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = []
    # Ownership
    user_id: Optional[int] = None
    org_id: Optional[int] = None
    user_email: Optional[str] = None
    username: Optional[str] = None


class JobListItem(BaseModel):
    job_id: str
    mode: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    completed_at: Optional[str] = None
    title: Optional[str] = None
    tags: list[str] = []
    # Ownership
    user_id: Optional[int] = None
    org_id: Optional[int] = None
    username: Optional[str] = None


class UpdateJobMeta(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None



# ── Batch sweep models ────────────────────────────────────────────────────────

_VALID_PARAMS = {"sats", "planes", "inclination", "altitude", "phasing", "weather"}
_VALID_MODES  = {"heatmap", "heatmap-rf", "coverage"}


class SweepParamRange(BaseModel):
    """One swept parameter dimension."""
    param: str
    values: list[float | str]

    @field_validator("param")
    @classmethod
    def _check_param(cls, v: str) -> str:
        if v not in _VALID_PARAMS:
            raise ValueError(f"Invalid param '{v}'. Must be one of: {_VALID_PARAMS}")
        return v


class BatchRequest(BaseModel):
    """Batch sweep job submission."""
    mode: str = "heatmap"
    comms: str = "vdes"
    weather: str = "clear"
    min_elev: float = 10.0
    res: float = 5.0
    fixed_params: dict[str, Any] = {}
    sweep_params: list[SweepParamRange] = []
    title: Optional[str] = None

    @field_validator("mode")
    @classmethod
    def _check_mode(cls, v: str) -> str:
        if v not in _VALID_MODES:
            raise ValueError(f"Invalid mode '{v}'. Must be one of: {_VALID_MODES}")
        return v


# ── Options response ──────────────────────────────────────────────────────────

class ConstellationPreset(BaseModel):
    sats: int
    planes: int
    altitude: float
    inclination: float
    phasing: int
    sso: bool
    description: str = ""


class ShellDef(BaseModel):
    sats: int
    planes: int
    inclination: float
    altitude_km: float
    phasing: int = 1
    name: Optional[str] = None


class MultiShellPreset(BaseModel):
    shells: list[ShellDef]
    description: str = ""


class OptionsResponse(BaseModel):
    comms_payloads: list[str]
    weather_scenarios: list[str]
    locations: list[str]
    sea_routes: list[str]
    arctic_routes: list[str]
    platforms: list[str]
    backends: list[str]
    constellation_presets: dict[str, ConstellationPreset] = {}
    known_constellations: dict[str, MultiShellPreset] = {}
    role: str = "viewer"
    limits: dict = {}
