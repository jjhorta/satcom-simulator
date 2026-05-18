from __future__ import annotations
from typing import Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Constellation shared params ───────────────────────────────────────────────

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


JobRequest = Union[HeatmapRequest, HeatmapRfRequest, SkyRequest, OrbitRequest, TrackRequest, RouteRequest]


# ── Job response models ───────────────────────────────────────────────────────

class JobFile(BaseModel):
    name: str
    type: Literal["csv", "png", "gif", "html", "txt", "log"]
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


class JobListItem(BaseModel):
    job_id: str
    mode: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    completed_at: Optional[str] = None
    title: Optional[str] = None
    tags: list[str] = []


class UpdateJobMeta(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None


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
