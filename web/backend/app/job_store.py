"""
File-based job store.
Each job is stored as a JSON file at {outputs_dir}/{job_id}/job.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import JobFile, JobListItem, JobStatus


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_dir(outputs_dir: Path, job_id: str) -> Path:
    return outputs_dir / job_id


def _job_meta_path(outputs_dir: Path, job_id: str) -> Path:
    return _job_dir(outputs_dir, job_id) / "job.json"


def _ext_to_type(name: str) -> str:
    ext = Path(name).suffix.lower().lstrip(".")
    if ext == "log":
        return "log"
    return ext if ext in ("csv", "png", "gif", "html", "txt") else "txt"


def create_job(outputs_dir: Path, job_id: str, mode: str, params: dict) -> JobStatus:
    job_dir = _job_dir(outputs_dir, job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    meta = JobStatus(
        job_id=job_id,
        mode=mode,
        status="queued",
        created_at=_now_iso(),
        params=params,
    )
    _job_meta_path(outputs_dir, job_id).write_text(meta.model_dump_json(), encoding="utf-8")
    return meta


def update_job(outputs_dir: Path, job_id: str, **kwargs) -> None:
    path = _job_meta_path(outputs_dir, job_id)
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(kwargs)
    path.write_text(json.dumps(data), encoding="utf-8")


def get_job(outputs_dir: Path, job_id: str, base_url: str = "") -> Optional[JobStatus]:
    path = _job_meta_path(outputs_dir, job_id)
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    job_dir = _job_dir(outputs_dir, job_id)

    # Build file list from directory contents
    files: list[JobFile] = []
    log_tail: Optional[str] = None

    for f in sorted(job_dir.iterdir()):
        if f.name == "job.json":
            continue
        ftype = _ext_to_type(f.name)
        files.append(JobFile(
            name=f.name,
            type=ftype,
            url=f"{base_url}/api/jobs/{job_id}/files/{f.name}",
            size_bytes=f.stat().st_size,
        ))
        if f.name == "job.log":
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                log_tail = "\n".join(lines[-50:])
            except Exception:
                pass

    data["files"] = [f.model_dump() for f in files]
    data["log_tail"] = log_tail
    return JobStatus(**data)


def list_jobs(outputs_dir: Path) -> list[JobListItem]:
    items = []
    if not outputs_dir.exists():
        return items
    for job_dir in sorted(outputs_dir.iterdir(), reverse=True):
        meta_path = job_dir / "job.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            items.append(JobListItem(
                job_id=data["job_id"],
                mode=data["mode"],
                status=data["status"],
                created_at=data["created_at"],
                completed_at=data.get("completed_at"),
                title=data.get("title"),
                tags=data.get("tags", []),
                user_id=data.get("user_id"),
                org_id=data.get("org_id"),
                username=data.get("username"),
            ))
        except Exception:
            continue
    return items
