"""Ground station registry — feeder link gateways for bent-pipe & regenerative architectures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

DEFAULT_GATEWAYS_PATH = Path(__file__).parent / "data" / "ground_stations.json"


@dataclass
class GroundStation:
    """A fixed Earth station providing feeder/uplink connectivity."""
    id: str
    name: str
    latitude: float
    longitude: float
    altitude_m: float = 0.0
    min_elevation: float = 5.0         # minimum elevation for feeder link
    freq_bands: list[str] = field(default_factory=lambda: ["vdes", "ais"])
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_m": self.altitude_m,
            "min_elevation": self.min_elevation,
            "freq_bands": self.freq_bands,
            "enabled": self.enabled,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GroundStation":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Default gateway catalogue ──────────────────────────────────────────────
# Maritime VDES feeder link gateways at coastal locations.
# Each entry pairs with a VDES-compatible comms payload.

DEFAULT_GATEWAYS: list[GroundStation] = [
    # Europe — Atlantic / Portugal EEZ
    GroundStation("sintra",     "Sintra, Portugal",        38.800, -9.383,  freq_bands=["vdes", "ais"], tags=["europe", "portugal"]),
    GroundStation("funchal",    "Funchal, Madeira",         32.633, -16.900, freq_bands=["vdes", "ais"], tags=["europe", "portugal"]),
    GroundStation("ponta_delgada", "Ponta Delgada, Azores", 37.733, -25.667, freq_bands=["vdes", "ais"], tags=["europe", "portugal"]),
    GroundStation("las_palmas", "Las Palmas, Canary Is.",   28.100, -15.417, freq_bands=["vdes", "ais"], tags=["europe", "atlantic"]),

    # Europe — North Sea / Baltic
    GroundStation("rotterdam",  "Rotterdam, Netherlands",   51.917,  4.500,  freq_bands=["vdes", "ais"], tags=["europe", "north-sea"]),
    GroundStation("bergen",     "Bergen, Norway",           60.350,  5.333,  freq_bands=["vdes", "ais"], tags=["europe", "north-sea"]),

    # Mediterranean
    GroundStation("gibraltar",  "Gibraltar",               36.140, -5.350,  freq_bands=["vdes", "ais"], tags=["mediterranean"]),
    GroundStation("valletta",   "Valletta, Malta",          35.900, 14.517,  freq_bands=["vdes", "ais"], tags=["mediterranean"]),
    GroundStation("piraeus",    "Piraeus, Greece",          37.933, 23.633,  freq_bands=["vdes", "ais"], tags=["mediterranean"]),

    # Middle East / Red Sea
    GroundStation("suez",       "Suez, Egypt",              29.967, 32.567,  freq_bands=["vdes", "ais", "ku"], tags=["middle-east"]),
    GroundStation("jeddah",     "Jeddah, Saudi Arabia",     21.483, 39.183,  freq_bands=["vdes", "ais"], tags=["middle-east"]),

    # Americas
    GroundStation("panama",     "Panama City, Panama",       8.983, -79.517, freq_bands=["vdes", "ais"], tags=["americas"]),
    GroundStation("miami",      "Miami, USA",               25.750, -80.200, freq_bands=["vdes", "ais", "ku"], tags=["americas"]),
    GroundStation("rio",        "Rio de Janeiro, Brazil",  -22.900, -43.200, freq_bands=["vdes", "ais"], tags=["americas"]),

    # Africa
    GroundStation("cape_town",  "Cape Town, South Africa", -33.917, 18.417,  freq_bands=["vdes", "ais"], tags=["africa"]),
    GroundStation("maputo",     "Maputo, Mozambique",      -25.967, 32.583,  freq_bands=["vdes", "ais"], tags=["africa"]),

    # Asia / Indian Ocean
    GroundStation("colombo",    "Colombo, Sri Lanka",        6.933, 79.850,  freq_bands=["vdes", "ais"], tags=["asia"]),
    GroundStation("singapore",  "Singapore",                 1.283, 103.833, freq_bands=["vdes", "ais", "ku"], tags=["asia"]),
    GroundStation("yokohama",   "Yokohama, Japan",          35.450, 139.650, freq_bands=["vdes", "ais"], tags=["asia"]),

    # Oceania
    GroundStation("sydney",     "Sydney, Australia",       -33.867, 151.200, freq_bands=["vdes", "ais"], tags=["oceania"]),
    GroundStation("auckland",   "Auckland, New Zealand",   -36.850, 174.750, freq_bands=["vdes", "ais"], tags=["oceania"]),
]


def load_gateways(outputs_dir: Path) -> list[GroundStation]:
    """Load gateway list from user-editable JSON, falling back to defaults."""
    path = outputs_dir / "ground_stations.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [GroundStation.from_dict(d) for d in data]
        except Exception:
            pass
    # First run — persist defaults
    save_gateways(outputs_dir, DEFAULT_GATEWAYS)
    return list(DEFAULT_GATEWAYS)


def save_gateways(outputs_dir: Path, gateways: list[GroundStation]) -> None:
    """Persist gateway list to JSON."""
    path = outputs_dir / "ground_stations.json"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([g.to_dict() for g in gateways], indent=2),
        encoding="utf-8",
    )


def get_feeder_link_gateways(
    gateways: list[GroundStation],
    freq_band: str = "vdes",
    region_tags: list[str] | None = None,
) -> list[GroundStation]:
    """Filter gateways by frequency band and optional region tags."""
    result = [g for g in gateways if g.enabled and freq_band in g.freq_bands]
    if region_tags:
        result = [g for g in result if any(t in g.tags for t in region_tags)]
    return result
