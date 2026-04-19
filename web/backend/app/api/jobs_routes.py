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
from ..job_store import create_job, get_job, list_jobs, update_job
from ..models import (
    HeatmapRequest, JobListItem, JobStatus, JobRequest,
    OrbitRequest, RouteRequest, SkyRequest, TrackRequest,
    UpdateJobMeta,
)
from ..settings_store import get_active_constellation_presets

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_DISPATCH = {
    "heatmap": HeatmapRequest,
    "sky": SkyRequest,
    "orbit": OrbitRequest,
    "track": TrackRequest,
    "route": RouteRequest,
}


def _get_queue(settings: Settings) -> Queue:
    redis_conn = Redis.from_url(settings.redis_url)
    return Queue(settings.rq_queue_name, connection=redis_conn)


@router.post("", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    payload: dict,
    request: Request,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
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

    job = create_job(settings.outputs_dir, job_id, mode, params)

    # Auto-generate tags from params + constellation presets
    try:
        presets = get_active_constellation_presets(settings.simulator_root, settings.outputs_dir)
        auto_tags = generate_autotags(mode, params, presets)
        update_job(settings.outputs_dir, job_id, tags=auto_tags)
    except Exception:
        pass  # tags are non-critical — never block submission

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


@router.get("", response_model=list[JobListItem])
async def list_all_jobs(
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    return list_jobs(settings.outputs_dir)


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    base_url = str(request.base_url).rstrip("/")
    job = get_job(settings.outputs_dir, job_id, base_url)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


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

    FLOAT_COLS = {"latitude", "longitude", "availability_pct", "connectivity_pct", "lat", "lon"}
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
    _: str = Depends(get_current_user),
):
    import shutil
    job_dir = settings.outputs_dir / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    shutil.rmtree(job_dir)
