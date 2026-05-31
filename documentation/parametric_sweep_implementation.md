# 🛰️ Parametric Batch Sweep — Implementation Specification

**Target:** Another LLM (Claude) implementing the batch parametric sweep engine.

**Goal:** Allow users to sweep Walker constellation parameters (sats, planes, inclination, altitude, phasing) across a grid and get comparative coverage heatmaps + metrics table + TCO comparison — all from the web UI.

**⚠️ PREREQUISITE:** This doc depends on the **Pricing & Subscription** system (`tier_config.py`, `stripe_integration.py`) and **Job Store** (`job_store.py`). Both are already implemented.

**⚠️ NOTE on existing `batch.sim.sh`:** That script was a one-off CLI study for comparing specific scenarios (12/3/1 vs 12/4/1 vs 24/8/1). It is NOT used by this feature. This spec builds a **new parametric engine** integrated into the web SaaS, reusing the core `sim/` modules directly.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Module: `sim/batch/sweep.py` — Parameter Grid Generator](#2-module-simbatchsweeppy)
3. [Module: `sim/batch/summary.py` — Comparative Report Generator](#3-module-simbatchsummarypy)
4. [Worker: `tasks.py` — Batch Job Runner](#4-worker-taskspy--batch-job-runner)
5. [API: `jobs_routes.py` — Batch Endpoint](#5-api-jobs_routespy--batch-endpoint)
6. [Backend Models: `models.py` — BatchRequest](#6-backend-models-modelspy--batchrequest)
7. [Tier Config: `tier_config.py` — Batch Limits](#7-tier-config-tier_configpy--batch-limits)
8. [Frontend: `BatchPage.tsx` — Sweep Submission](#8-frontend-batchpagetsx--sweep-submission)
9. [Frontend: `BatchResultViewer.tsx` — Results Dashboard](#9-frontend-batchresultviewertsx--results-dashboard)
10. [Validation](#10-validation)
11. [Implementation Order](#11-implementation-order)
12. [Potential Pitfalls](#12-potential-pitfalls)

---

## 1. Architecture Overview

### Data Flow

```
User opens BatchPage.tsx
  → Defines parameter ranges (sats=[12,24,48], inc=[53,87], altitude=[550,600])
  → POST /api/jobs/batch {sweep_params, mode:"heatmap"}

Backend: jobs_routes.py
  → Validates limits from tier_config (max_sweep_combinations, max_batch_jobs)
  → Creates a single "batch" JobStatus record with status="queued"
  → Enqueues ONE RQ job with the sweep definition

Worker: tasks.py → run_batch_job()
  → Generates parameter grid (Cartesian product of all ranges)
  → For each combo: runs the simulator subprocess (same as single-job mode)
  → Collects outputs into {job_dir}/{combo_index}/
  → Generates summary: comparative CSV + heatmap grid PNG + optional TCO comparison
  → Updates job status to "completed" with summary files

Frontend: BatchResultViewer.tsx
  → Polls job status like normal jobs
  → Displays summary CSV, heatmap grid image, individual results
  → Side-by-side metrics comparison table
```

### File Layout

```
sim/
├── batch/
│   ├── __init__.py            ← NEW: empty
│   ├── sweep.py               ← NEW: parameter grid generation
│   └── summary.py             ← NEW: comparative report generation

web/backend/
├── app/
│   ├── models.py              ← MODIFY: add SweepParamRange, BatchRequest models
│   ├── tier_config.py         ← MODIFY: add batch_limits per tier
│   ├── api/
│   │   └── jobs_routes.py     ← MODIFY: add POST /api/jobs/batch endpoint
│   └── worker/
│       └── tasks.py           ← MODIFY: add run_batch_job() task

web/frontend/src/
├── types.ts                   ← MODIFY: add SweepDef, SweepResult types
├── api/client.ts              ← MODIFY: add submitBatchJob(), getSweepResults()
├── pages/
│   ├── BatchPage.tsx          ← NEW: sweep configuration form
│   └── DashboardPage.tsx      ← MODIFY: add "Batch Sweep" tab/button
├── components/
│   └── BatchResultViewer.tsx  ← NEW: sweep results dashboard
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Sweep as parent job** | Single job record, worker fans out internally | Reuses existing job polling, file serving, and UI patterns |
| **Parameter grid** | Cartesian product of 1D ranges | Simple, predictable, covers all common use cases |
| **Output organization** | Subdir per combo + summary at root | Individual results are independent; summary aggregates |
| **Concurrency** | Sequential within batch (one sim at a time) | Respects tier concurrency limits; worker runs them back-to-back |
| **Stopping a batch** | Flag file check after each sub-sim | `{job_dir}/.cancel` — worker checks between iterations |
| **Reuse mode runners** | Call existing `run_heatmap()`, `run_coverage()` via subprocess | Zero duplication of simulation logic |

---

## 2. Module: `sim/batch/sweep.py`

```
CREATE: sim/batch/__init__.py (empty)
CREATE: sim/batch/sweep.py
```

```python
"""
Parametric sweep — generate Walker constellation parameter grids.

Supports:
- Range: (start, stop, step) using numpy.linspace semantics
- Values: explicit list of values
- Cartesian product of all parameter dimensions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Literal

import numpy as np


@dataclass
class SweepParam:
    """Definition of one swept parameter dimension."""
    param: str  # one of: 'sats', 'planes', 'inclination', 'altitude', 'phasing'
    values: list[float]  # explicit list of values

    @classmethod
    def from_range(cls, param: str, start: float, stop: float, step: float | int) -> "SweepParam":
        """Generate values from start to stop (inclusive)."""
        if param in ("sats", "planes", "phasing"):
            values = list(range(int(start), int(stop) + 1, int(step)))
        else:
            num = max(2, int(round((stop - start) / step)) + 1)
            values = list(np.linspace(start, stop, num))
            values = [round(v, 1) for v in values]
        return cls(param=param, values=values)


@dataclass
class SweepDefinition:
    """Complete sweep definition — generates all configurations."""
    mode: Literal["heatmap", "coverage"]
    comms: str = "vdes"
    weather: str = "clear"
    min_elev: float = 10.0
    res: float = 5.0
    duration: int = 3600
    fixed_params: dict[str, Any] = field(default_factory=dict)
    sweep_params: list[SweepParam] = field(default_factory=list)

    def generate_configs(self) -> list[dict[str, Any]]:
        """Generate all parameter combinations (Cartesian product)."""
        if not self.sweep_params:
            return [self.fixed_params.copy()]
        dim_values = [sp.values for sp in self.sweep_params]
        dim_names = [sp.param for sp in self.sweep_params]
        configs = []
        for combo in product(*dim_values):
            config = self.fixed_params.copy()
            for name, val in zip(dim_names, combo):
                config[name] = val
            configs.append(config)
        return configs

    @property
    def num_configs(self) -> int:
        if not self.sweep_params:
            return 1
        return int(np.prod([len(sp.values) for sp in self.sweep_params]))

    def label_for(self, config: dict[str, Any]) -> str:
        """Human-readable label e.g. 's48_p6_i53_a600'."""
        parts = []
        for sp in self.sweep_params:
            val = config.get(sp.param)
            if sp.param == "sats":
                parts.append(f"s{int(val)}")
            elif sp.param == "planes":
                parts.append(f"p{int(val)}")
            elif sp.param == "inclination":
                parts.append(f"i{val:.0f}")
            elif sp.param == "altitude":
                parts.append(f"a{int(val)}")
            elif sp.param == "phasing":
                parts.append(f"f{int(val)}")
        return "_".join(parts) if parts else "default"
```

---

## 3. Module: `sim/batch/summary.py`

```
CREATE: sim/batch/summary.py
```

```python
"""
Comparative summary generator for batch sweeps.

Produces:
1. Summary CSV: one row per config with coverage metrics
2. Summary JSON: same data structured for frontend consumption
3. Heatmap grid: side-by-side PNG comparison with labels
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def extract_metrics(heatmap_csv: Path) -> dict[str, float]:
    """Parse heatmap CSV and extract coverage statistics."""
    availabilities = []
    with open(heatmap_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                availabilities.append(float(row["availability_pct"]))
            except (ValueError, KeyError):
                continue
    if not availabilities:
        return {"mean_coverage_pct": 0.0, "max_coverage_pct": 0.0,
                "min_coverage_pct": 0.0, "coverage_above_90_pct": 0.0,
                "coverage_above_50_pct": 0.0}
    arr = np.array(availabilities)
    total = len(arr)
    return {
        "mean_coverage_pct": float(np.mean(arr)),
        "max_coverage_pct": float(np.max(arr)),
        "min_coverage_pct": float(np.min(arr)),
        "coverage_above_90_pct": float(np.sum(arr >= 90.0) / total * 100),
        "coverage_above_50_pct": float(np.sum(arr >= 50.0) / total * 100),
    }


def generate_summary_csv(results: list[dict[str, Any]], output_path: Path) -> Path:
    """Generate comparative CSV with coverage metrics per config."""
    param_cols = list(results[0]["params"].keys()) if results else []
    fieldnames = (["config", "status"] + param_cols +
                  ["mean_coverage_pct", "max_coverage_pct", "min_coverage_pct",
                   "coverage_above_90_pct", "coverage_above_50_pct"])
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            if not r["success"]:
                row = {"config": r["label"], "status": "FAILED"}
                for col in param_cols:
                    row[col] = r["params"].get(col, "")
                writer.writerow(row)
                continue
            metrics = extract_metrics(r["heatmap_csv"])
            writer.writerow({"config": r["label"], "status": "OK",
                             **r["params"], **metrics})
    return output_path


def generate_summary_json(results: list[dict[str, Any]], output_path: Path) -> Path:
    """Generate JSON summary for frontend consumption."""
    summary = []
    for r in results:
        entry = {"label": r["label"], "params": r["params"], "success": r["success"]}
        if r["success"] and r.get("heatmap_csv"):
            entry["metrics"] = extract_metrics(r["heatmap_csv"])
            if r.get("tco_json"):
                try:
                    entry["tco"] = json.loads(Path(r["tco_json"]).read_text())
                except Exception:
                    entry["tco"] = None
        summary.append(entry)
    output_path.write_text(json.dumps(summary, indent=2, default=float))
    return output_path


def generate_heatmap_grid(results: list[dict[str, Any]], output_path: Path,
                          grid_cols: int = 4) -> Path:
    """Generate a grid PNG of heatmap thumbnails for side-by-side comparison."""
    from PIL import Image, ImageDraw, ImageFont
    valid = [r for r in results if r["success"] and r.get("heatmap_png")]
    if not valid:
        return output_path
    n = len(valid)
    cols = min(grid_cols, n)
    rows = math.ceil(n / cols)
    first_img = Image.open(valid[0]["heatmap_png"])
    thumb_w, thumb_h = first_img.size
    scale = 0.4
    cell_w = int(thumb_w * scale)
    cell_h = int(thumb_h * scale)
    label_h = 30
    grid_w = cols * cell_w
    grid_h = rows * (cell_h + label_h)
    grid_img = Image.new("RGB", (grid_w, grid_h), (30, 30, 30))
    draw = ImageDraw.Draw(grid_img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for idx, r in enumerate(valid):
        col = idx % cols
        row_idx = idx // cols
        x = col * cell_w
        y = row_idx * (cell_h + label_h)
        draw.text((x + 4, y + 2), r["label"], fill=(200, 200, 200), font=font)
        thumb = Image.open(r["heatmap_png"])
        thumb.thumbnail((cell_w, cell_h), Image.LANCZOS)
        grid_img.paste(thumb, (x, y + label_h))
    grid_img.save(output_path, "PNG")
    return output_path
```

---

## 4. Worker: `tasks.py` — Batch Job Runner

**MODIFY:** `web/backend/worker/tasks.py`

### New imports

```python
from sim.batch.sweep import SweepDefinition, SweepParam
from sim.batch.summary import generate_summary_csv, generate_summary_json, generate_heatmap_grid
```

### New function: `run_batch_job()`

```python
def run_batch_job(job_id: str, simulator_root: str, outputs_dir: str,
                  sweep_def: dict, user_id: int, tier: str) -> None:
    """
    Run a parametric batch sweep.

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

        cmd = [str(venv_python), str(satsim_script), sd.mode,
               f"--sats={int(config.get('sats', 66))}",
               f"--planes={int(config.get('planes', 6))}",
               f"--inclination={config.get('inclination', 87.4)}",
               f"--altitude={config.get('altitude', 600.0)}",
               f"--phasing={int(config.get('phasing', 1))}",
               f"--comms={sd.comms}",
               f"--weather={sd.weather}",
               f"--min-elev={sd.min_elev}",
               f"--res={sd.res}",
               "--save"]
        if sd.mode == "coverage":
            cmd.append(f"--duration={sd.duration}")

        result = {"label": label, "params": config, "success": False}
        try:
            subprocess.run(cmd, cwd=str(combo_dir), timeout=3600,
                          capture_output=True, text=True, check=True)
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
                [grid_png] + [r.get("heatmap_png") for r in results if r.get("heatmap_png")], tier)
        _update_batch_meta(job_dir, {
            "status": "completed", "completed": total,
            "summary_csv": "sweep_summary.csv",
            "summary_json": "sweep_summary.json",
            "heatmap_grid": "sweep_heatmap_grid.png",
        })
    except Exception as e:
        _update_batch_meta(job_dir, {"status": "failed", "error": str(e)})


def _update_batch_meta(job_dir: Path, updates: dict) -> None:
    meta_path = job_dir / "job.json"
    if meta_path.exists():
        data = json.loads(meta_path.read_text())
        data.update(updates)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(json.dumps(data))


def _fail_batch(job_dir: Path, error: str) -> None:
    _update_batch_meta(job_dir, {"status": "failed", "error": error})


def _tier_needs_watermark(tier: str) -> bool:
    return tier in ("viewer", "free")


def _apply_watermark_multiple(paths: list[Path], tier: str) -> None:
    try:
        from ..app.watermark import should_watermark, apply_watermark
        if should_watermark(tier):
            for p in paths:
                if p and p.exists():
                    apply_watermark(str(p))
    except ImportError:
        pass
```

---

## 5. API: `jobs_routes.py` — Batch Endpoint

**MODIFY:** `web/backend/app/api/jobs_routes.py`

```python
@router.post("/batch", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def submit_batch_job(
    body: BatchRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    role = get_effective_role(user)
    if not has_permission(role, "jobs:create"):
        raise HTTPException(status_code=403, detail="Your role does not allow creating simulations")

    limits = get_limits(role)
    max_combos = limits.get("max_sweep_combinations", 0)
    max_batch_jobs = limits.get("max_batch_jobs_per_month", 0)

    if max_combos == 0:
        raise HTTPException(status_code=403, detail="Batch simulations not available on your plan")

    total_combos = 1
    for sp in body.sweep_params:
        total_combos *= len(sp.values)
    if total_combos > max_combos:
        raise HTTPException(status_code=422,
            detail=f"Too many combinations ({total_combos}). Max for {role}: {max_combos}")

    jobs_used = user.get("batch_jobs_used_this_month", 0)
    if max_batch_jobs != -1 and jobs_used >= max_batch_jobs:
        raise HTTPException(status_code=429, detail="Monthly batch job limit reached")

    job_id = str(uuid.uuid4())
    params = body.model_dump()
    params["total_combinations"] = total_combos
    meta = create_job(settings.outputs_dir, job_id, "batch", params)

    queue = _get_queue(settings)
    queue.enqueue(
        "worker.tasks.run_batch_job",
        args=(job_id, settings.simulator_root, str(settings.outputs_dir),
              body.model_dump(), user["id"], role),
        job_timeout=86400,
    )
    return meta
```

---

## 6. Backend Models: `models.py`

Add to `web/backend/app/models.py`:

```python
class SweepParamRange(BaseModel):
    param: Literal["sats", "planes", "inclination", "altitude", "phasing"]
    values: list[float]

class BatchRequest(BaseModel):
    mode: Literal["heatmap", "coverage"] = "heatmap"
    comms: str = "vdes"
    weather: str = "clear"
    min_elev: float = 10.0
    res: float = 5.0
    fixed_params: dict[str, Any] = {}
    sweep_params: list[SweepParamRange] = []
    title: Optional[str] = None
```

Also update `JobFile.type` to include `"json"`.

---

## 7. Tier Config: `tier_config.py` — Batch Limits

**MODIFY:** `web/backend/app/tier_config.py`

Add to each tier dict:

```python
# viewer / free
"batch_sweep": False,
"max_sweep_combinations": 0,
"max_batch_jobs_per_month": 0,

# demo
"batch_sweep": False,
"max_sweep_combinations": 0,
"max_batch_jobs_per_month": 0,

# creator (Pro)
"batch_sweep": True,
"max_sweep_combinations": 50,
"max_batch_jobs_per_month": 5,

# team_manager (Enterprise)
"batch_sweep": True,
"max_sweep_combinations": 200,
"max_batch_jobs_per_month": 20,

# admin
"batch_sweep": True,
"max_sweep_combinations": 500,
"max_batch_jobs_per_month": 100,
```

---

## 8. Frontend: `BatchPage.tsx` — Sweep Submission

**CREATE:** `web/frontend/src/pages/BatchPage.tsx`

Layout:

```
┌─────────────────────────────────────────────────┐
│  🛰️ Parametric Sweep Engine                      │
│                                                   │
│  ┌─ Simulation Mode ──────────────────────────┐   │
│  │  ● Heatmap    ○ Coverage                   │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ Walker Parameters to Sweep ───────────────┐   │
│  │  Satellites: 12  24  48           [Remove] │   │
│  │  Planes: 3  4  6  8              [Remove] │   │
│  │  Inclination: 53  87             [Remove] │   │
│  │  Altitude: 550  600  650         [Remove] │   │
│  │  [+ Add Parameter]                         │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ Fixed Parameters ─────────────────────────┐   │
│  │  Comms: ● VDES ○ AIS ○ MSS ○ Ku           │   │
│  │  Weather: ● Clear ○ Storm ○ Tropical       │   │
│  │  Grid Resolution: [5.0°]                   │   │
│  │  Min Elevation: [10.0°]                    │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ Summary ─────────────────────────────────┐   │
│  │  3 params × 3 values each                  │   │
│  │  = 27 configurations                       │   │
│  │  Est. time: ~15 minutes                    │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  [🚀 Start Sweep]                                  │
└─────────────────────────────────────────────────┘
```

Key state types:

```tsx
interface SweepParamDef {
  param: 'sats' | 'planes' | 'inclination' | 'altitude' | 'phasing';
  values: number[];
}

interface SweepFormState {
  mode: 'heatmap' | 'coverage';
  comms: string;
  weather: string;
  minElev: number;
  resolution: number;
  sweepParams: SweepParamDef[];
}
```

### Route

```tsx
// App.tsx
<Route path="/batch" element={<RequireAuth><BatchPage /></RequireAuth>} />
```

---

## 9. Frontend: `BatchResultViewer.tsx` — Results Dashboard

**CREATE:** `web/frontend/src/components/BatchResultViewer.tsx`

Shows:

```
┌─────────────────────────────────────────────────┐
│  ✅ Batch Sweep Complete (27/27)  [Rerun] [DL]  │
│                                                   │
│  ┌─ Summary Table (sortable) ────────────────┐   │
│  │  Config         │ MeanCov │ >90%  │ >50%  │   │
│  │  s12_p4_i53_a550 │ 32.1%   │ 5.2%  │ 28%   │   │
│  │  s12_p4_i53_a600 │ 30.5%   │ 4.8%  │ 25%   │   │
│  │  s12_p6_i53_a550 │ 38.7%   │ 8.1%  │ 33%   │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ Heatmap Grid ────────────────────────────┐   │
│  │  [s12_p4]  [s12_p6]  [s24_p4]  [s24_p6] │   │
│  │  [s48_p4]  [s48_p6]                       │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ Individual Results ──────────────────────┐   │
│  │  ▸ s12_p4_i53_a550: [heatmap] [CSV] [GEO] │   │
│  │  ▸ s12_p4_i53_a600: [heatmap] [CSV] [GEO] │   │
│  └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

Types:

```tsx
interface SweepResultEntry {
  label: string;
  params: Record<string, number>;
  success: boolean;
  metrics?: {
    mean_coverage_pct: number;
    max_coverage_pct: number;
    min_coverage_pct: number;
    coverage_above_90_pct: number;
    coverage_above_50_pct: number;
  };
}
```

Polling: same as existing job polling. Show progress bar while `running` using `completed/total` from job meta.

---

## 10. Validation

### Test 1: Basic Sweep (3 params × 2 values = 8 combos)

```bash
curl -X POST http://localhost:8000/api/jobs/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "heatmap",
    "sweep_params": [
      {"param": "sats", "values": [12, 24]},
      {"param": "inclination", "values": [53.0, 87.0]},
      {"param": "altitude", "values": [550, 600]}
    ]
  }'
```

Expected: HTTP 202, after completion job dir has `sweep_summary.csv`, `.json`, `sweep_heatmap_grid.png`.

### Test 2: Permission

```bash
# As viewer
curl -X POST ... /api/jobs/batch ...
```
Expected: HTTP 403.

### Test 3: Combo Limit

```bash
curl -X POST ... -d '{
  "sweep_params": [
    {"param": "sats", "values": [12, 24, 48, 96]},
    {"param": "inclination", "values": [53, 60, 70, 80, 87]},
    {"param": "altitude", "values": [500, 550, 600, 650, 700]}
  ]
}'
```
Expected: HTTP 422.

### Test 4: Cancellation

```bash
touch /path/to/outputs/{job_id}/.cancel
```
Expected: Job status → cancelled.

### Test 5: Frontend E2E

- Open `/batch` as Pro user
- Fill form with sats=[12,24], planes=[3,4], inc=[53]
- Verify combo count = 4
- Submit → see job in dashboard list → open results on completion

---

## 11. Implementation Order

| # | File | Action |
|---|------|--------|
| 1 | `sim/batch/__init__.py` | Create |
| 2 | `sim/batch/sweep.py` | Create |
| 3 | `sim/batch/summary.py` | Create |
| 4 | `web/backend/app/models.py` | Modify (add models) |
| 5 | `web/backend/app/tier_config.py` | Modify (add limits) |
| 6 | `web/backend/worker/tasks.py` | Modify (add run_batch_job) |
| 7 | `web/backend/app/api/jobs_routes.py` | Modify (add batch endpoint) |
| 8 | `web/frontend/src/types.ts` | Modify |
| 9 | `web/frontend/src/api/client.ts` | Modify |
| 10 | `web/frontend/src/pages/BatchPage.tsx` | Create |
| 11 | `web/frontend/src/components/BatchResultViewer.tsx` | Create |
| 12 | `web/frontend/src/App.tsx` | Modify (add route) |
| 13 | `web/frontend/src/pages/DashboardPage.tsx` | Modify (add entry point) |

---

## 12. Potential Pitfalls

### ⚠️ Long-Running Jobs
200 combos × 2 min ≈ 7h. RQ timeout must be 86400s.
**Mitigation**: Show estimated time, allow `.cancel` flag, save progress every 5 combos.

### ⚠️ Disk Space
1 combo ≈ 1-5 MB. 200 combos ≈ 1 GB. Hard cap at 200.

### ⚠️ Watermark on Grid
Apply watermark to grid PNG for free tiers.

### ⚠️ Worker Restart Mid-Batch
In-memory `results` lost on restart.
**Mitigation**: Append to `results.jsonl` after each combo; resume by scanning existing dirs.

### ⚠️ Progress Display
Frontend needs `completed/total` for batch jobs.
**Mitigation**: `get_job()` returns `params.total_combinations` and `completed` count.

### ⚠️ Existing batch.sim.sh
Don't delete. The new system lives in `sim/batch/` — no conflict.
