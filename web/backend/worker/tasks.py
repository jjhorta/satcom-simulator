"""
RQ worker tasks — run simulator as a subprocess.

The simulator is invoked with the venv Python from the simulator root.
PYTHONPATH is set so the `sim` package is importable even though cwd=output_dir.
All simulator output files land in output_dir (cwd).
Settings overrides (comms/weather constants) are injected via a PYTHONSTARTUP
script that monkey-patches sim.constants before the simulator runs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sim.batch.sweep import SweepDefinition, SweepParam
from sim.batch.summary import generate_summary_csv, generate_summary_json, generate_heatmap_grid


# ── Watermark helper ──────────────────────────────────────────────


def _apply_watermark(output_dir: str, tier: str) -> None:
    """Apply watermark to PNG outputs if the user is on free tier."""
    from pathlib import Path
    try:
        from ..app.watermark import should_watermark, apply_watermark
        if should_watermark(tier):
            for f in Path(output_dir).glob("*.png"):
                apply_watermark(str(f))
    except ImportError:
        pass  # watermark module not available


# ── Path helpers ──────────────────────────────────────────────────────────────

def _simulator_root(simulator_root: str) -> Path:
    return Path(simulator_root)


def _venv_python(simulator_root: str) -> Path:
    """Prefer the simulator venv; fall back to current interpreter."""
    candidate = _simulator_root(simulator_root) / "venv" / "bin" / "python3"
    return candidate if candidate.exists() else Path(sys.executable)


def _satsim_script(simulator_root: str) -> Path:
    return _simulator_root(simulator_root) / "satsim_radio.py"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Settings override helpers ─────────────────────────────────────────────────

def _load_settings_overrides(outputs_dir: str) -> dict:
    """Load settings.json override file if it exists."""
    path = Path(outputs_dir) / "settings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_patcher_script(overrides: dict) -> str | None:
    """
    Write a temporary PYTHONSTARTUP script that monkey-patches sim.constants
    with user overrides when the subprocess starts.
    Returns the temp file path, or None if there are no overrides.
    """
    comms = overrides.get("comms_payloads", {})
    weather = overrides.get("weather_scenarios", {})
    sea = overrides.get("sea_routes", {})
    arctic = overrides.get("arctic_routes", {})
    tco = overrides.get("tco_config", {})
    if not comms and not weather and not sea and not arctic and not tco:
        return None

    lines = [
        "import sys, importlib",
        "def _patch_constants():",
        "    try:",
        "        c = importlib.import_module('sim.constants')",
    ]
    for tech, fields in comms.items():
        for field, val in fields.items():
            lines.append(f"        if {repr(tech)} in c.COMMS_PAYLOADS: c.COMMS_PAYLOADS[{repr(tech)}][{repr(field)}] = {repr(val)}")
    for scenario, val in weather.items():
        lines.append(f"        if {repr(scenario)} in c.WEATHER_SCENARIOS: c.WEATHER_SCENARIOS[{repr(scenario)}] = {repr(val)}")
    for route_name, wps in sea.items():
        lines.append(f"        c.SEA_ROUTES[{repr(route_name)}] = [tuple(wp) for wp in {repr(wps)}]")
    for route_name, wps in arctic.items():
        lines.append(f"        c.ARCTIC_ROUTES[{repr(route_name)}] = [tuple(wp) for wp in {repr(wps)}]")
    if tco:
        lines.append(f"        _tco_ovr = {repr(tco)}")
        lines.append("        def _dm(b, o):")
        lines.append("            for k, v in o.items():")
        lines.append("                b[k] = _dm(b[k], v) if isinstance(b.get(k), dict) and isinstance(v, dict) else v")
        lines.append("            return b")
        lines.append("        _dm(c.TCO_CONFIG, _tco_ovr)")
    lines += [
        "    except Exception:",
        "        pass",
        "_patch_constants()",
    ]

    script = "\n".join(lines) + "\n"
    fd, path = tempfile.mkstemp(suffix=".py", prefix="sim_patcher_")
    with os.fdopen(fd, "w") as f:
        f.write(script)
    return path


# ── Job store helpers (inlined to avoid import path issues in worker) ─────────

def _update_job_meta(output_dir: Path, job_id: str, **kwargs) -> None:
    meta_path = output_dir / "job.json"
    if meta_path.exists():
        data: dict = json.loads(meta_path.read_text(encoding="utf-8"))
        data.update(kwargs)
        meta_path.write_text(json.dumps(data), encoding="utf-8")


# ── CLI builder ───────────────────────────────────────────────────────────────

def _flag(key: str) -> str:
    """Convert snake_case param key to --kebab-case CLI flag."""
    # A few mode-specific overrides (CLI flag != param key).
    OVERRIDES = {
        "from_location": "--from",
        "to_location":   "--to",
    }
    if key in OVERRIDES:
        return OVERRIDES[key]
    return f"--{key.replace('_', '-')}"


def _build_command(
    python: Path,
    script: Path,
    mode: str,
    params: dict[str, Any],
) -> list[str]:
    """
    Build the satsim_radio.py command line from mode + params dict.

    satsim_radio.py structure:
        satsim_radio.py [--backend BACKEND] <subcommand> [subcommand-flags...]

    All constellation geometry flags (--sats, --planes, etc.) belong to the
    subcommand, not the top-level parser.
    --save is only accepted by: sky, orbit, track, route  (NOT heatmap).
    """
    # Modes that support --save
    MODES_WITH_SAVE = {"sky", "orbit", "track", "route"}

    # Keys that must never be emitted as CLI flags
    SKIP_PARAMS = {
        "backend",   # handled explicitly before subcommand
        "mode",      # IS the subcommand
        "sso",       # handled explicitly as a boolean flag
        "constellation",       # handled explicitly below
        "constellation_name",  # handled explicitly below
        "shells",    # handled explicitly below
        # Constellation geometry handled in explicit loop below
        "sats", "planes", "altitude", "phasing", "inclination",
        "_user_id", "_org_id", "_role", "_user_email",
    }

    cmd = [str(python), str(script)]

    # ── Only truly global flag ─────────────────────────────────────────────
    cmd += ["--backend", str(params.get("backend", "matplotlib"))]

    # ── Subcommand ─────────────────────────────────────────────────────────
    cmd.append(mode)

    # ── Constellation geometry or multi-shell preset ───────────────────────
    constellation = params.get("constellation")
    constellation_name = params.get("constellation_name")  # pure label, no lookup
    shells = params.get("shells")
    if shells and isinstance(shells, list) and len(shells) > 0:
        # --shells always wins when provided (covers both user groups and named presets)
        import json as _json
        cmd += ["--shells", _json.dumps(shells)]
        label = constellation_name or constellation
        if label:
            cmd += ["--constellation-name", str(label)]
    elif constellation:
        # Built-in KNOWN_CONSTELLATIONS name — pass directly
        cmd += ["--constellation", str(constellation)]
    else:
        for key in ("sats", "planes", "altitude", "phasing", "inclination"):
            val = params.get(key)
            if val is not None:
                cmd += [_flag(key), str(val)]
        if params.get("sso"):
            cmd.append("--sso")

    # ── Mode-specific flags ─────────────────────────────────────────────────
    for key, val in params.items():
        if key in SKIP_PARAMS:
            continue
        if val is True:
            cmd.append(_flag(key))
        elif val is False or val is None:
            continue
        else:
            cmd += [_flag(key), str(val)]

    # ── --save only for modes that support it ──────────────────────────────
    if mode in MODES_WITH_SAVE:
        cmd.append("--save")

    return cmd


# ── Main task ─────────────────────────────────────────────────────────────────

def run_simulation(
    job_id: str,
    mode: str,
    params: dict[str, Any],
    outputs_dir: str,
    simulator_root: str,
) -> dict:
    """
    RQ task entry point.

    Parameters
    ----------
    job_id        : internal job identifier
    mode          : 'heatmap' | 'sky' | 'orbit' | 'track' | 'route'
    params        : flat dict of CLI param names → values
    outputs_dir   : absolute path to the web outputs directory  (e.g. /app/outputs)
    simulator_root: absolute path to the constellation_simulator directory
    """
    output_dir = Path(outputs_dir) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "job.log"

    # Mark job as running
    _update_job_meta(output_dir, job_id, status="running", started_at=_now_iso())

    python = _venv_python(simulator_root)
    script = _satsim_script(simulator_root)

    if not script.exists():
        error_msg = f"Simulator script not found: {script}"
        _update_job_meta(output_dir, job_id, status="failed",
                         completed_at=_now_iso(), error=error_msg)
        return {"status": "failed", "error": error_msg}

    try:
        # Resolve user-created multi-shell constellation names to shell definitions.
        # Built-in KNOWN_CONSTELLATIONS names are passed directly via --constellation.
        # User-created groups (not in KNOWN_CONSTELLATIONS) are resolved here and
        # passed as --shells JSON + --constellation-name for labeling.
        params = dict(params)  # copy so we don't mutate caller's dict
        constellation_param = params.get("constellation")
        if constellation_param and not params.get("shells"):
            # Check if it's a built-in name; if not, resolve from settings.json directly.
            # We read settings.json here to avoid fragile relative-import paths in the worker.
            known_names: set[str] = set()
            try:
                sim_path = str(_simulator_root(simulator_root))
                import sys as _sys
                if sim_path not in _sys.path:
                    _sys.path.insert(0, sim_path)
                import importlib as _importlib
                _c = _importlib.import_module("sim.constants")
                known_names = set(getattr(_c, "KNOWN_CONSTELLATIONS", {}).keys())
            except Exception:
                pass

            if constellation_param not in known_names:
                # User-created group — resolve shells from settings.json directly
                settings_path = Path(outputs_dir) / "settings.json"
                try:
                    settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
                    user_groups = settings_data.get("multi_shell_groups", {})
                    group = user_groups.get(constellation_param)
                    if group and not group.get("deleted") and group.get("shells"):
                        params["shells"] = group["shells"]
                        params["constellation_name"] = constellation_param
                        params["constellation"] = None  # clear so --shells path is taken
                except Exception:
                    pass  # settings.json missing or unreadable — argparse will give clear error

        cmd = _build_command(python, script, mode, params)
    except KeyError as exc:
        error_msg = f"Unknown mode: {exc}"
        _update_job_meta(output_dir, job_id, status="failed",
                         completed_at=_now_iso(), error=error_msg)
        return {"status": "failed", "error": error_msg}

    # Set PYTHONPATH so `sim` package is importable from any cwd
    env = os.environ.copy()
    # Read tier from job metadata
    try:
        meta_path = Path(output_dir) / "job.json"
        if meta_path.exists():
            job_meta = json.loads(meta_path.read_text())
            env["CONSTELLATION_SIM_TIER"] = job_meta.get("role", "viewer")
        else:
            env["CONSTELLATION_SIM_TIER"] = "viewer"
    except Exception:
        env["CONSTELLATION_SIM_TIER"] = "viewer"
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{simulator_root}:{existing_pp}" if existing_pp else simulator_root
    )

    # Inject settings overrides via PYTHONSTARTUP monkey-patch
    overrides = _load_settings_overrides(outputs_dir)
    patcher_path = _write_patcher_script(overrides)
    if patcher_path:
        env["PYTHONSTARTUP"] = patcher_path

    # Write the command to the log for debugging
    with open(log_path, "w", encoding="utf-8") as log_fh:
        log_fh.write(f"[{_now_iso()}] Running command:\n")
        log_fh.write(" ".join(cmd) + "\n\n")

        proc = subprocess.run(
            cmd,
            cwd=str(output_dir),
            env=env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3600,  # 1-hour hard limit per job
        )

    # Clean up temp patcher script
    if patcher_path:
        try:
            os.unlink(patcher_path)
        except Exception:
            pass

    if proc.returncode == 0:
        status = "completed"
        error = None
    else:
        status = "failed"
        # Grab last 20 lines of log as error summary
        try:
            all_lines = log_path.read_text(encoding="utf-8").splitlines()
            error = "\n".join(all_lines[-20:])
        except Exception:
            error = f"Process exited with code {proc.returncode}"

    files = [
        f.name for f in sorted(output_dir.iterdir())
        if f.name not in ("job.json", "job.log") and f.is_file()
    ]

    _update_job_meta(
        output_dir, job_id,
        status=status,
        completed_at=_now_iso(),
        error=error,
        files=files,
    )

    return {"status": status, "files": files, "return_code": proc.returncode}


# ── Batch sweep task ──────────────────────────────────────────────────────────

def run_batch_job(
    job_id: str,
    simulator_root: str,
    outputs_dir: str,
    sweep_def: dict,
    user_id: int,
    tier: str,
) -> None:
    """
    RQ task for parametric batch sweep.

    sweep_def example:
    {
        "mode": "heatmap",
        "comms": "vdes",
        "weather": "clear",
        "min_elev": 10.0,
        "res": 5.0,
        "fixed_params": {},
        "sweep_params": [
            {"param": "sats", "values": [12, 24, 48]},
            {"param": "inclination", "values": [53.0, 87.0]},
            {"param": "altitude", "values": [550.0, 600.0]}
        ]
    }
    """
    job_dir = Path(outputs_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    sps = [SweepParam(**sp) for sp in sweep_def.get("sweep_params", [])]
    fixed = sweep_def.get("fixed_params", {})
    sd = SweepDefinition(
        mode=sweep_def["mode"],
        comms=sweep_def.get("comms", "vdes"),
        weather=sweep_def.get("weather", "clear"),
        min_elev=sweep_def.get("min_elev", 10.0),
        res=sweep_def.get("res", 5.0),
        duration=sweep_def.get("duration", 3600),
        fixed_params=fixed,
        sweep_params=sps,
    )

    configs = sd.generate_configs()
    total = len(configs)

    if total == 0:
        _fail_batch(job_dir, "No configurations generated from sweep params")
        return
    if total > 200:
        _fail_batch(job_dir, f"Too many combinations ({total}). Max is 200.")
        return

    _update_batch_meta(job_dir, {"status": "running", "total": total, "completed": 0})

    venv_python = _venv_python(simulator_root)
    satsim_script = _satsim_script(simulator_root)
    results = []

    for idx, config in enumerate(configs):
        if (job_dir / ".cancel").exists():
            _update_batch_meta(job_dir, {"status": "cancelled", "completed": idx})
            return

        label = sd.label_for(config)
        combo_dir = job_dir / str(idx)
        combo_dir.mkdir(exist_ok=True)

        cmd = [
            str(venv_python), str(satsim_script), "--backend", "matplotlib", sd.mode,
            f"--sats={int(config.get('sats', 66))}",
            f"--planes={int(config.get('planes', 6))}",
            f"--inclination={config.get('inclination', 87.4)}",
            f"--altitude={config.get('altitude', 600.0)}",
            f"--phasing={int(config.get('phasing', 1))}",
            f"--comms={sd.comms}",
            f"--weather={config.get('weather', sd.weather)}",
            f"--min-elev={sd.min_elev}",
            f"--res={sd.res}",
        ]
        if sd.mode == "heatmap-rf":
            cmd.append("--bidi")
        if sd.mode in {"sky", "orbit", "track", "route"}:
            cmd.append("--save")
        if sd.mode == "coverage":
            cmd.append(f"--duration={sd.duration}")

        result = {"label": label, "params": config, "success": False}
        try:
            subprocess.run(
                cmd, cwd=str(combo_dir), timeout=3600,
                capture_output=True, text=True, check=True,
            )
            csv_files = list(combo_dir.glob("heatmap_*.csv"))
            png_files = list(combo_dir.glob("heatmap_*.png"))
            if csv_files:
                result["heatmap_csv"] = csv_files[0]
            if png_files:
                result["heatmap_png"] = png_files[0]
            tco_files = list(combo_dir.glob("*tco*.json"))
            if tco_files:
                result["tco_json"] = tco_files[0]
            result["success"] = True
        except subprocess.TimeoutExpired:
            result["error"] = "TIMEOUT"
        except subprocess.CalledProcessError as e:
            result["error"] = (e.stderr or "")[:500]
            (combo_dir / "error.log").write_text(e.stderr or "(empty)")

        results.append(result)
        if idx % 5 == 0 or idx == total - 1:
            _update_batch_meta(job_dir, {"completed": idx + 1})

    try:
        summary_csv = job_dir / "sweep_summary.csv"
        generate_summary_csv(results, summary_csv)
        summary_json = job_dir / "sweep_summary.json"
        generate_summary_json(results, summary_json)
        grid_png = job_dir / "sweep_heatmap_grid.png"
        generate_heatmap_grid(results, grid_png)
        if tier and _tier_needs_watermark(tier):
            _apply_watermark_multiple(
                [grid_png] + [r.get("heatmap_png") for r in results if r.get("heatmap_png")],
                tier,
            )
        _update_batch_meta(job_dir, {
            "status": "completed",
            "completed": total,
            "summary_csv": "sweep_summary.csv",
            "summary_json": "sweep_summary.json",
            "heatmap_grid": "sweep_heatmap_grid.png",
        })
    except Exception as e:
        _update_batch_meta(job_dir, {"status": "failed", "error": str(e)})


def _update_batch_meta(job_dir: Path, updates: dict) -> None:
    """Update the batch job's meta file."""
    meta_path = job_dir / "job.json"
    if meta_path.exists():
        data = json.loads(meta_path.read_text())
        data.update(updates)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(json.dumps(data))


def _fail_batch(job_dir: Path, error: str) -> None:
    """Mark a batch job as failed."""
    _update_batch_meta(job_dir, {"status": "failed", "error": error})


def _tier_needs_watermark(tier: str) -> bool:
    """Check if output needs watermark."""
    return tier in ("viewer", "free")


def _apply_watermark_multiple(paths: list[Path], tier: str) -> None:
    """Apply watermark to multiple PNG files."""
    try:
        from ..app.watermark import should_watermark, apply_watermark
        if should_watermark(tier):
            for p in paths:
                if p and p.exists():
                    apply_watermark(str(p))
    except ImportError:
        pass
