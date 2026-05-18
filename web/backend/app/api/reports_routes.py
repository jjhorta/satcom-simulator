"""
reports_routes.py — server-side persistence for Full Report metadata.

Stored in {outputs_dir}/reports.json as a JSON array of ReportState objects.
Share tokens stored in {outputs_dir}/report_shares.json.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from ..auth import get_current_user
from ..config import Settings, get_settings

router = APIRouter(prefix="/api/reports", tags=["reports"])

_REPORTS_FILE        = "reports.json"
_SHARES_FILE         = "report_shares.json"
_SHARE_SETTINGS_FILE = "share_settings.json"

# ── Password hashing (pure stdlib — no passlib/bcrypt needed) ─────────────────

def _hash_pw(password: str) -> str:
    """PBKDF2-SHA256 with a random 16-byte salt, 260 000 iterations."""
    salt   = os.urandom(16)
    dk     = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return base64.b64encode(salt).decode() + ":" + base64.b64encode(dk).decode()


def _verify_pw(password: str, stored: str) -> bool:
    try:
        salt_b64, dk_b64 = stored.split(":", 1)
        salt  = base64.b64decode(salt_b64)
        dk    = base64.b64decode(dk_b64)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
        return secrets.compare_digest(check, dk)
    except Exception:
        return False


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load(outputs_dir: Path) -> list:
    p = outputs_dir / _REPORTS_FILE
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(outputs_dir: Path, reports: list) -> None:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / _REPORTS_FILE).write_text(
        json.dumps(reports, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_shares(outputs_dir: Path) -> dict:
    """Returns {token: {report_id, password_hash}}"""
    p = outputs_dir / _SHARES_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_shares(outputs_dir: Path, shares: dict) -> None:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / _SHARES_FILE).write_text(
        json.dumps(shares, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_share_settings(outputs_dir: Path) -> dict:
    p = outputs_dir / _SHARE_SETTINGS_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_share_settings(outputs_dir: Path, data: dict) -> None:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / _SHARE_SETTINGS_FILE).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Report CRUD ───────────────────────────────────────────────────────────────

@router.get("")
async def list_reports(
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return all saved reports (most recent first)."""
    return _load(settings.outputs_dir)


@router.post("")
async def upsert_report(
    body: dict,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Create or update a report by reportId (upsert semantics)."""
    report_id = body.get("reportId")
    if not report_id:
        raise HTTPException(status_code=400, detail="reportId is required")

    reports = _load(settings.outputs_dir)
    idx = next((i for i, r in enumerate(reports) if r.get("reportId") == report_id), None)
    if idx is not None:
        reports[idx] = body
    else:
        reports.insert(0, body)

    _save(settings.outputs_dir, reports)
    return reports


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Delete a report by reportId."""
    reports = _load(settings.outputs_dir)
    reports = [r for r in reports if r.get("reportId") != report_id]
    _save(settings.outputs_dir, reports)
    # Also clean up any share tokens for this report
    shares = _load_shares(settings.outputs_dir)
    shares = {t: s for t, s in shares.items() if s.get("report_id") != report_id}
    _save_shares(settings.outputs_dir, shares)
    return reports


# ── Share endpoints ───────────────────────────────────────────────────────────

@router.post("/{report_id}/share")
async def share_report(
    report_id: str,
    body: dict,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Generate a public share token for a report.
    Body: {password: str}  (required — at least 4 chars)
    Returns: {token: str}
    """
    password = (body.get("password") or "").strip()
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Share password must be at least 4 characters.")

    reports = _load(settings.outputs_dir)
    if not any(r.get("reportId") == report_id for r in reports):
        raise HTTPException(status_code=404, detail="Report not found.")

    token = secrets.token_urlsafe(16)
    password_hash = _hash_pw(password)

    shares = _load_shares(settings.outputs_dir)
    # Revoke any existing token for this report
    shares = {t: s for t, s in shares.items() if s.get("report_id") != report_id}
    shares[token] = {"report_id": report_id, "password_hash": password_hash}
    _save_shares(settings.outputs_dir, shares)

    # Persist token back onto the report
    for r in reports:
        if r.get("reportId") == report_id:
            r["shareToken"] = token
            break
    _save(settings.outputs_dir, reports)

    return {"token": token}


@router.get("/shared/{token}")
async def get_shared_report(
    token: str,
    password: str = "",
    settings: Settings = Depends(get_settings),
):
    """
    Public (unauthenticated) endpoint — returns a report if password matches.
    Query param: ?password=<the share password>
    Returns the report without aiInsights.
    """
    shares = _load_shares(settings.outputs_dir)
    share  = shares.get(token)
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found or expired.")

    if not password or not _verify_pw(password, share["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password.")

    report_id = share["report_id"]
    reports   = _load(settings.outputs_dir)
    report    = next((r for r in reports if r.get("reportId") == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report no longer exists.")

    # Strip private fields before returning
    safe = {k: v for k, v in report.items() if k != "aiInsights"}
    return safe


# ── Share default password settings ──────────────────────────────────────────

@router.get("/share-settings")
async def get_share_settings(
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return whether a default share password is configured."""
    data = _load_share_settings(settings.outputs_dir)
    return {"has_default_password": bool(data.get("default_password_hash"))}


@router.put("/share-settings")
async def update_share_settings(
    body: dict,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Set or clear the default share password.
    Body: {password: str}  — empty string clears it.
    """
    password = (body.get("password") or "").strip()
    data = _load_share_settings(settings.outputs_dir)
    if password:
        if len(password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
        data["default_password_hash"] = _hash_pw(password)
        data["default_password_preview"] = password[:2] + "***"
    else:
        data.pop("default_password_hash", None)
        data.pop("default_password_preview", None)
    _save_share_settings(settings.outputs_dir, data)
    return {"has_default_password": bool(data.get("default_password_hash"))}


# ── Shared file/TCO proxy (public, no auth) ───────────────────────────────────

_FILE_MEDIA_TYPES = {
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".html": "text/html",
    ".csv":  "text/csv",
    ".txt":  "text/plain",
    ".log":  "text/plain",
    ".json": "application/json",
}


def _verify_shared_job(token: str, job_id: str, password: str, outputs_dir: Path) -> None:
    """Raise 401/404 if the token+password don't grant access to the job."""
    shares = _load_shares(outputs_dir)
    share  = shares.get(token)
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found or expired.")
    if not password or not _verify_pw(password, share["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password.")

    # Verify the job belongs to the shared report
    report_id = share["report_id"]
    reports   = _load(outputs_dir)
    report    = next((r for r in reports if r.get("reportId") == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report no longer exists.")

    all_jobs: list[str] = []
    jobs = report.get("jobs", {})
    if jobs.get("heatmap"):   all_jobs.append(jobs["heatmap"])
    if jobs.get("heatmapRf"): all_jobs.append(jobs["heatmapRf"])
    if jobs.get("orbit"):     all_jobs.append(jobs["orbit"])
    all_jobs.extend(jobs.get("routes", {}).values())

    if job_id not in all_jobs:
        raise HTTPException(status_code=403, detail="Job does not belong to this shared report.")


@router.get("/shared/{token}/jobs/{job_id}/files")
async def shared_job_files(
    token: str,
    job_id: str,
    password: str = "",
    settings: Settings = Depends(get_settings),
):
    """Return the list of filenames for a shared job (no JWT required)."""
    _verify_shared_job(token, job_id, password, settings.outputs_dir)
    job_dir = settings.outputs_dir / job_id
    files = [
        f.name for f in sorted(job_dir.iterdir())
        if f.is_file() and f.name not in ("job.json", "job.log")
    ]
    return {"files": files}


@router.get("/shared/{token}/jobs/{job_id}/csv/{filename}")
async def shared_csv_proxy(
    token: str,
    job_id: str,
    filename: str,
    password: str = "",
    settings: Settings = Depends(get_settings),
):
    """Return CSV as JSON array for a shared report (no JWT required)."""
    import csv as _csv
    _verify_shared_job(token, job_id, password, settings.outputs_dir)
    safe_name = Path(filename).name
    if not safe_name.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Not a CSV file")
    file_path = settings.outputs_dir / job_id / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    FLOAT_COLS = {"latitude", "longitude", "availability_pct", "rf_availability_pct", "connectivity_pct", "lat", "lon"}
    INT_COLS   = {"sequence"}
    content = file_path.read_text(encoding="utf-8")
    reader = _csv.DictReader(content.splitlines())
    rows = []
    for row in reader:
        rows.append({
            k: int(v)   if k in INT_COLS   else
               float(v) if k in FLOAT_COLS else v
            for k, v in row.items()
        })
    return rows


@router.get("/shared/{token}/jobs/{job_id}/files/{filename}")
async def shared_file_proxy(
    token: str,
    job_id: str,
    filename: str,
    password: str = "",
    settings: Settings = Depends(get_settings),
):
    """Proxy a job file for a shared report (no JWT required)."""
    _verify_shared_job(token, job_id, password, settings.outputs_dir)
    safe_name = Path(filename).name
    file_path = settings.outputs_dir / job_id / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    media_type = _FILE_MEDIA_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=safe_name)


@router.get("/shared/{token}/jobs/{job_id}/tco")
async def shared_tco_proxy(
    token: str,
    job_id: str,
    password: str = "",
    settings: Settings = Depends(get_settings),
):
    """Proxy TCO data for a shared report (no JWT required)."""
    _verify_shared_job(token, job_id, password, settings.outputs_dir)
    job_dir = settings.outputs_dir / job_id
    matches = sorted(job_dir.glob("tco_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="TCO data not available for this job.")
    try:
        return json.loads(matches[0].read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read TCO data.")


