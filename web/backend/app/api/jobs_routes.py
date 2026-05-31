import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from redis import Redis
from rq import Queue

from ..auth import get_current_user
from ..autotags import generate_autotags
from ..config import Settings, get_settings
from ..db import increment_demo_job_count
from ..job_store import create_job, get_job, list_jobs, update_job
from ..models import (
    HeatmapRequest, HeatmapRfRequest, JobListItem, JobStatus, JobRequest,
    LatencyRequest, OrbitRequest, RouteRequest, SkyRequest, TrackRequest,
    SweepParamRange, BatchRequest,
    UpdateJobMeta,
)
from ..rbac import get_effective_role, has_permission, demo_is_expired
from ..tier_config import get_limits, validate_job_params
from ..settings_store import get_active_constellation_presets

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_DISPATCH = {
    "heatmap":    HeatmapRequest,
    "heatmap-rf": HeatmapRfRequest,
    "sky":        SkyRequest,
    "orbit":      OrbitRequest,
    "track":      TrackRequest,
    "route":      RouteRequest,
    "latency":    LatencyRequest,
}


def _get_queue(settings: Settings) -> Queue:
    redis_conn = Redis.from_url(settings.redis_url)
    return Queue(settings.rq_queue_name, connection=redis_conn)


@router.post("", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    payload: dict,
    request: Request,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    role = get_effective_role(user)

    # Permission check
    if not has_permission(role, "jobs:create"):
        raise HTTPException(status_code=403, detail="Your role does not allow creating simulations")

    # Demo limits
    if role == "demo":
        if demo_is_expired(user):
            raise HTTPException(status_code=403, detail="Demo period has expired")
        used  = user.get("demo_jobs_used", 0) or 0
        limit = user.get("demo_jobs_limit", 10) or 10
        if used >= limit:
            raise HTTPException(status_code=429, detail="Demo simulation limit reached")

    # Monthly job quota check
    limits = get_limits(role)
    monthly_limit = limits.get("jobs_per_month", 0)
    jobs_used = user.get("jobs_used_this_month", 0)
    if monthly_limit != -1 and jobs_used >= monthly_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly job limit reached ({monthly_limit}/{monthly_limit}). Upgrade or wait.",
        )

    mode = payload.get("mode")
    if mode not in _DISPATCH:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    # Validate with the mode-specific model
    try:
        job_req = _DISPATCH[mode](**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    job_id = str(uuid.uuid4())
    params = job_req.model_dump()

    # Validate params against role limits
    errors = validate_job_params(role, params)
    if errors:
        raise HTTPException(status_code=403, detail="; ".join(errors))

    job = create_job(settings.outputs_dir, job_id, mode, params)

    # Store ownership metadata
    update_job(
        settings.outputs_dir, job_id,
        user_id=user.get("id"),
        org_id=user.get("org_id"),
        user_email=user.get("email", ""),
        username=user.get("username", ""),
    )

    # Auto-generate tags from params + constellation presets
    try:
        presets = get_active_constellation_presets(settings.simulator_root, settings.outputs_dir)
        auto_tags = generate_autotags(mode, params, presets)
        update_job(settings.outputs_dir, job_id, tags=auto_tags)
    except Exception:
        pass  # tags are non-critical — never block submission

    # Increment demo job counter
    if role == "demo" and user.get("id"):
        increment_demo_job_count(settings.outputs_dir, user["id"])

    # Enqueue RQ task
    q = _get_queue(settings)
    q.enqueue(
        "worker.tasks.run_simulation",
        kwargs={
            "job_id": job_id,
            "mode": mode,
            "params": params,
            "outputs_dir": str(settings.outputs_dir),
            "simulator_root": str(settings.simulator_root),
        },
        job_timeout=3600,
        job_id=job_id,
    )

    base_url = str(request.base_url).rstrip("/")
    return get_job(settings.outputs_dir, job_id, base_url)


@router.post("/batch", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def submit_batch_job(
    body: BatchRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    """Submit a parametric batch sweep job."""
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
        raise HTTPException(
            status_code=422,
            detail=f"Too many combinations ({total_combos}). Max for {role}: {max_combos}",
        )

    jobs_used = user.get("batch_jobs_used_this_month", 0)
    if max_batch_jobs != -1 and jobs_used >= max_batch_jobs:
        raise HTTPException(status_code=429, detail="Monthly batch job limit reached")

    job_id = str(uuid.uuid4())
    params = body.model_dump()
    params["total_combinations"] = total_combos
    meta = create_job(settings.outputs_dir, job_id, "batch", params)

    # Auto-generate tags for the batch job
    try:
        tags = generate_autotags("batch", body.model_dump(), {})
        update_job(settings.outputs_dir, job_id, tags=tags)
    except Exception:
        pass  # tags are best-effort

    queue = _get_queue(settings)
    queue.enqueue(
        "worker.tasks.run_batch_job",
        args=(
            job_id,
            settings.simulator_root,
            str(settings.outputs_dir),
            body.model_dump(),
            user["id"],
            role,
        ),
        job_timeout=86400,
    )
    return meta


@router.get("", response_model=list[JobListItem])
async def list_all_jobs(
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    role = get_effective_role(user)
    all_jobs = list_jobs(settings.outputs_dir)

    if has_permission(role, "jobs:view_team"):
        if role == "admin":
            return all_jobs  # admin sees everything
        # team_manager sees own org
        org_id = user.get("org_id")
        return [j for j in all_jobs if j.org_id == org_id or j.user_id == user.get("id")]
    elif has_permission(role, "jobs:view_own"):
        return [j for j in all_jobs if j.user_id == user.get("id")]
    return []


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    base_url = str(request.base_url).rstrip("/")
    job = get_job(settings.outputs_dir, job_id, base_url)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Scope check
    role = get_effective_role(user)
    if not _can_access_job(job, user, role):
        raise HTTPException(status_code=403, detail="Access denied")
    return job


def _can_access_job(job, user: dict, role: str) -> bool:
    if has_permission(role, "jobs:delete_any"):
        return True
    if has_permission(role, "jobs:view_team"):
        return job.org_id == user.get("org_id") or job.user_id == user.get("id")
    return job.user_id == user.get("id")


@router.get("/{job_id}/files/{filename}")
async def download_file(
    job_id: str,
    filename: str,
    settings: Settings = Depends(get_settings),
):
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    file_path = settings.outputs_dir / job_id / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        ".png": "image/png",
        ".gif": "image/gif",
        ".html": "text/html",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".log": "text/plain",
        ".json": "application/json",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=safe_name)


@router.get("/{job_id}/combo/{combo_index}/{filename}")
async def download_combo_file(
    job_id: str,
    combo_index: str,
    filename: str,
    settings: Settings = Depends(get_settings),
):
    """Serve a file from a batch sweep combo subdirectory."""
    safe_name = Path(filename).name
    safe_idx = Path(combo_index).name
    file_path = settings.outputs_dir / job_id / safe_idx / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_types = {
        ".png": "image/png",
        ".gif": "image/gif",
        ".html": "text/html",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".log": "text/plain",
        ".json": "application/json",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=f"{safe_idx}_{safe_name}")


@router.get("/{job_id}/tco")
async def get_tco_data(
    job_id: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return the TCO JSON for an orbit job."""
    import json
    job_dir = settings.outputs_dir / job_id
    matches = sorted(job_dir.glob("tco_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="No TCO data found for this job")
    data = json.loads(matches[0].read_text(encoding="utf-8"))
    return data


@router.get("/{job_id}/tles")
async def get_tles(
    job_id: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return saved TLE JSON for an orbit job."""
    import json
    job_dir = settings.outputs_dir / job_id
    matches = sorted(job_dir.glob("tles_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="No TLE data found for this job")
    return json.loads(matches[0].read_text(encoding="utf-8"))


@router.get("/{job_id}/ai-analysis")
async def get_ai_analysis(
    job_id: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return the saved AI analysis text for a job."""
    cache_file = settings.outputs_dir / job_id / "ai_analysis.txt"
    if not cache_file.exists():
        raise HTTPException(status_code=404, detail="No AI analysis saved for this job")
    return {"text": cache_file.read_text(encoding="utf-8")}


@router.post("/{job_id}/ai-analysis", status_code=201)
async def save_ai_analysis(
    job_id: str,
    payload: dict,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Persist AI analysis text for a job."""
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    job_dir = settings.outputs_dir / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    (job_dir / "ai_analysis.txt").write_text(text, encoding="utf-8")
    return {"saved": True}


@router.get("/{job_id}/csv/{filename}")
async def get_csv_as_json(
    job_id: str,
    filename: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return CSV content as JSON array for map rendering."""
    import csv
    safe_name = Path(filename).name
    if not safe_name.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Not a CSV file")
    file_path = settings.outputs_dir / job_id / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    FLOAT_COLS = {"latitude", "longitude", "availability_pct", "rf_availability_pct", "connectivity_pct", "lat", "lon"}
    INT_COLS   = {"sequence"}
    rows = []
    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        content = await f.read()
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        rows.append({
            k: int(v)   if k in INT_COLS   else
               float(v) if k in FLOAT_COLS else v
            for k, v in row.items()
        })
    return rows


@router.patch("/{job_id}", response_model=JobStatus)
async def update_job_meta(
    job_id: str,
    body: UpdateJobMeta,
    request: Request,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Update title, description, and/or tags of a job."""
    job = get_job(settings.outputs_dir, job_id, str(request.base_url).rstrip("/"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Use model_dump with exclude_unset so that explicitly-set empty lists (tags=[]) are included
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if patch:
        update_job(settings.outputs_dir, job_id, **patch)
    return get_job(settings.outputs_dir, job_id, str(request.base_url).rstrip("/"))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    import shutil
    job_dir = settings.outputs_dir / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    job = get_job(settings.outputs_dir, job_id)
    role = get_effective_role(user)

    if has_permission(role, "jobs:delete_any"):
        pass
    elif has_permission(role, "jobs:delete_team"):
        if job and job.org_id != user.get("org_id"):
            raise HTTPException(status_code=403, detail="Access denied")
    elif has_permission(role, "jobs:delete_own"):
        if job and job.user_id != user.get("id"):
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    shutil.rmtree(job_dir)
