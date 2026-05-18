"""
autotags.py — Automatic tag generation for simulation jobs.

Tags are derived purely from the job parameters and active constellation
presets.  No side effects; returns a sorted, deduplicated list of strings.
"""
from __future__ import annotations


def generate_autotags(mode: str, params: dict, presets: dict) -> list[str]:
    """Return auto-generated tags for a simulation job.

    Args:
        mode:    Simulation mode (heatmap, sky, orbit, route, track).
        params:  Validated parameter dict from the job request model.
        presets: Active constellation presets dict  {name: {sats, planes, …}}.
    """
    tags: set[str] = set()

    # ── 1. Simulation mode ─────────────────────────────────────────────────
    tags.add(mode)

    # ── Multi-shell: tag constellation name and override sats/alt for tiers ─
    _ms_sats: int | None = None
    _ms_alt: float | None = None
    constellation = params.get("constellation") or params.get("constellation_name")
    shells = params.get("shells")
    if constellation:
        tags.add(_slug(str(constellation)))
        tags.add("multi-shell")
    if shells and isinstance(shells, list):
        tags.add("multi-shell")
        try:
            _ms_sats = sum(int(s.get("sats", 0)) for s in shells)
            alts = [float(s.get("altitude_km", s.get("altitude", 600))) for s in shells if s.get("altitude_km") or s.get("altitude")]
            if alts:
                _ms_alt = min(alts)  # classify by lowest shell
        except (TypeError, ValueError):
            pass

    # ── 2. Constellation preset match (reverse geometry lookup) ────────────
    if not constellation and not shells:
        preset_name = _match_preset(params, presets)
        if preset_name:
            tags.add(_slug(preset_name))

    # ── 3. SSO ─────────────────────────────────────────────────────────────
    if params.get("sso"):
        tags.add("sso")

    # ── 4. Comms technology ────────────────────────────────────────────────
    comms = params.get("comms")
    if comms:
        tags.add(comms.lower())

    # ── 5. Weather (skip 'clear' — it's the default / unremarkable) ────────
    weather = params.get("weather", "clear")
    if weather and weather != "clear":
        tags.add(f"wx:{weather}")

    # ── 6. Route name ──────────────────────────────────────────────────────
    route = params.get("route")
    if route:
        tags.add(_slug(route))

    # ── 7. Location (sky / sky-coverage modes) ─────────────────────────────
    location = params.get("location")
    if location:
        tags.add(_slug(location))

    # ── 8. Coverage area (sky mode) ────────────────────────────────────────
    coverage = params.get("coverage")
    if coverage:
        tags.add(f"cov:{_slug(coverage)}")

    # ── 9. Orbital altitude band ───────────────────────────────────────────
    try:
        alt = _ms_alt if _ms_alt is not None else float(params.get("altitude", 600))
    except (TypeError, ValueError):
        alt = 600.0
    if alt < 2000:
        tags.add("leo")
    elif alt < 35_786:
        tags.add("meo")
    else:
        tags.add("geo")

    # ── 10. Constellation size tier ────────────────────────────────────────
    try:
        sats = _ms_sats if _ms_sats is not None else int(params.get("sats", 0))
    except (TypeError, ValueError):
        sats = 0
    if sats <= 20:
        tags.add("nano-const")
    elif sats <= 100:
        tags.add("small-const")
    elif sats <= 500:
        tags.add("mid-const")
    else:
        tags.add("mega-const")

    # ── 11. Bi-directional link ────────────────────────────────────────────
    if params.get("bidi"):
        tags.add("bidi")

    # ── 12. Satellite platform (orbit mode) ───────────────────────────────
    platform = params.get("platform")
    if platform:
        tags.add(platform)

    # ── 13. Resolution hint (heatmap mode) ────────────────────────────────
    res = params.get("res")
    if res is not None:
        try:
            r = float(res)
            if r <= 1.0:
                tags.add("high-res")
            elif r >= 10.0:
                tags.add("low-res")
        except (TypeError, ValueError):
            pass

    # ── 14. Min elevation hint ─────────────────────────────────────────────
    min_elev = params.get("min_elev")
    if min_elev is not None:
        try:
            if float(min_elev) >= 20.0:
                tags.add("high-elev")
        except (TypeError, ValueError):
            pass

    return sorted(tags)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _slug(s: str) -> str:
    """Lowercase, replace underscores/spaces with hyphens, trim."""
    return s.lower().replace("_", "-").replace(" ", "-").strip("-")


def _match_preset(params: dict, presets: dict) -> str | None:
    """Reverse-match params geometry against known presets."""
    try:
        p_sats   = int(params.get("sats",        -1))
        p_planes = int(params.get("planes",      -1))
        p_alt    = float(params.get("altitude",  -1))
        p_inc    = float(params.get("inclination", -1))
        p_phase  = int(params.get("phasing",     -1))
    except (TypeError, ValueError):
        return None

    for name, p in presets.items():
        try:
            if (
                int(p.get("sats",   -2)) == p_sats   and
                int(p.get("planes", -2)) == p_planes  and
                abs(float(p.get("altitude",    -2)) - p_alt) < 0.5 and
                abs(float(p.get("inclination", -2)) - p_inc) < 0.5 and
                int(p.get("phasing", -2)) == p_phase
            ):
                return name
        except (TypeError, ValueError):
            continue
    return None
