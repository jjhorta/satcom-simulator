"""
ai_routes.py — AI configuration management and server-side LLM proxy.

Security model:
  • API key stored server-side only (ai_config.json in outputs_dir)
  • Browser receives only: key_is_set (bool), masked_key ("****abcd"), model, base_url, system_prompt
  • LLM call made server-side; key never transmitted to or from the browser
  • All routes require JWT authentication
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..auth import get_current_user
from ..config import Settings, get_settings
from ..ai_config_store import feature_gate, load_config, public_status, save_config

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── Config endpoints ──────────────────────────────────────────────────────────

@router.get("/config")
async def get_ai_config(
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """Return safe (masked) AI config for the settings UI."""
    return public_status(settings.outputs_dir)


@router.put("/config")
async def update_ai_config(
    payload: dict,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Update AI config. Only provided fields are changed.
    Pass api_key as empty string to leave existing key unchanged.
    """
    allowed = {"api_key", "base_url", "model", "system_prompt"}
    patch = {k: v for k, v in payload.items() if k in allowed}
    if not patch:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    save_config(settings.outputs_dir, patch)
    return public_status(settings.outputs_dir)


# ── Server-side LLM streaming proxy ──────────────────────────────────────────

@router.post("/jobs/{job_id}/stream")
async def stream_ai_analysis(
    job_id: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
):
    """
    Server-side streaming proxy:
      1. Validates API key is configured (feature gate)
      2. Builds context from job output files (logs + CSV summaries)
      3. Calls the LLM API with Authorization header server-side
      4. Streams SSE back to the browser — key never exposed

    The saved ai_analysis.txt is also written upon completion.
    """
    cfg = feature_gate(settings.outputs_dir)
    if cfg is None:
        raise HTTPException(status_code=400, detail="AI API key not configured. Set it in Settings → AI.")

    job_dir = settings.outputs_dir / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    # ── Build context from job files ─────────────────────────────────────────
    chunks: list[str] = []

    # Job mode from job metadata
    job_meta_path = job_dir / "job.json"
    job_mode = "unknown"
    if job_meta_path.exists():
        try:
            meta = json.loads(job_meta_path.read_text(encoding="utf-8"))
            job_mode = meta.get("mode", "unknown")
        except Exception:
            pass

    chunks.append(f"# Simulation: {job_mode} | Job {job_id}\n")

    # Text / log files (up to 8000 chars each)
    for fpath in sorted(job_dir.glob("*.txt")) + sorted(job_dir.glob("*.log")):  # type: ignore[operator]
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            chunks.append(f"\n## File: {fpath.name}\n```\n{text[:8000]}\n```")
        except Exception:
            pass

    # CSV files — route as full table, heatmap as statistical summary
    for fpath in sorted(job_dir.glob("*.csv")):
        try:
            raw = fpath.read_text(encoding="utf-8", errors="replace")
            lines = raw.strip().split("\n")
            header = lines[0]
            rows = lines[1:]

            if fpath.name.startswith("route_"):
                cols = header.split(",")
                md_header = "| " + " | ".join(cols) + " |"
                md_sep    = "| " + " | ".join("---" for _ in cols) + " |"
                md_rows   = "\n".join(
                    "| " + " | ".join(c.strip() for c in r.split(",")) + " |"
                    for r in rows
                )
                chunks.append(f"\n## Data: {fpath.name} (Route waypoints)\n{md_header}\n{md_sep}\n{md_rows}")

            elif fpath.name.startswith("heatmap_"):
                col_names = header.split(",")
                lat_idx = col_names.index("latitude") if "latitude" in col_names else -1
                pct_idx = next(
                    (i for i, c in enumerate(col_names) if "availability_pct" in c or "pct" in c), -1
                )
                if lat_idx < 0 or pct_idx < 0:
                    chunks.append(f"\n## Data: {fpath.name}\n(Could not parse columns: {header})")
                    continue

                data = []
                for r in rows:
                    parts = r.split(",")
                    try:
                        data.append((float(parts[lat_idx]), float(parts[pct_idx])))
                    except (ValueError, IndexError):
                        pass

                if not data:
                    continue

                pcts = [d[1] for d in data]
                mean_p = sum(pcts) / len(pcts)
                min_p  = min(pcts)
                max_p  = max(pcts)
                below10 = sum(1 for p in pcts if p < 10)
                below50 = sum(1 for p in pcts if p < 50)
                above90 = sum(1 for p in pcts if p >= 90)

                bands = [
                    ("Arctic   (60–90°N)",  60,  90),
                    ("N.Temp.  (30–60°N)",  30,  60),
                    ("Tropics  (30°S–30°N)", -30, 30),
                    ("S.Temp.  (30–60°S)", -60, -30),
                    ("Antarct. (60–90°S)", -90, -60),
                ]
                band_lines = []
                for label, bmin, bmax in bands:
                    pts = [d[1] for d in data if bmin <= d[0] < bmax]
                    if not pts:
                        band_lines.append(f"  {label}: no data")
                        continue
                    avg = sum(pts) / len(pts)
                    band_lines.append(
                        f"  {label}: avg={avg:.1f}%  min={min(pts):.1f}%  max={max(pts):.1f}%"
                    )

                chunks.append(
                    f"\n## Data: {fpath.name} (Heatmap statistics, {len(data)} grid points)\n"
                    f"Global: mean={mean_p:.1f}%  min={min_p:.1f}%  max={max_p:.1f}%\n"
                    f"Points < 10%: {below10} ({below10/len(data)*100:.1f}%)\n"
                    f"Points < 50%: {below50} ({below50/len(data)*100:.1f}%)\n"
                    f"Points ≥ 90%: {above90} ({above90/len(data)*100:.1f}%)\n"
                    f"\nBy latitude band:\n" + "\n".join(band_lines)
                )
            else:
                # Generic CSV: first 50 rows
                preview = "\n".join([header] + rows[:50])
                chunks.append(f"\n## Data: {fpath.name}\n```csv\n{preview}\n```")

        except Exception:
            pass

    if len(chunks) <= 1:
        raise HTTPException(status_code=400, detail="No output files found for this job.")

    user_content = "\n".join(chunks)
    endpoint = cfg["base_url"].rstrip("/") + "/chat/completions"

    async def generate():
        collected = []
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {cfg['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": cfg["model"],
                        "stream": True,
                        "messages": [
                            {"role": "system", "content": cfg["system_prompt"]},
                            {"role": "user",   "content": user_content},
                        ],
                    },
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        err = body.decode("utf-8", errors="replace")[:300]
                        yield f"data: {json.dumps({'error': f'LLM API {resp.status_code}: {err}'})}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                collected.append(delta)
                                yield f"data: {json.dumps({'delta': delta})}\n\n"
                        except Exception:
                            pass

            # Persist completed analysis
            full_text = "".join(collected)
            if full_text:
                (job_dir / "ai_analysis.txt").write_text(full_text, encoding="utf-8")
            yield "data: [DONE]\n\n"

        except httpx.TimeoutException:
            yield f"data: {json.dumps({'error': 'LLM request timed out after 120 s'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)[:300]})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
