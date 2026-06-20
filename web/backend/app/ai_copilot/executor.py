"""CARL tool executor — calls internal APIs to fulfill tool requests."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx


async def execute_tool_call(
    tool_call: dict[str, Any],
    base_url: str,
    token: str,
    outputs_dir: Path,
) -> dict[str, Any]:
    """Execute a single tool call and return the result."""
    name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return {"tool_call_id": tool_call.get("id", ""), "name": name, "content": "Invalid JSON arguments"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    api = base_url.rstrip("/")

    try:
        if name == "submit_simulation":
            mode = args.get("mode", "heatmap")
            payload = {
                "mode": mode,
                "sats": int(args.get("sats", 66)),
                "planes": int(args.get("planes", 6)),
                "inclination": float(args.get("inclination", 87.4)),
                "altitude": float(args.get("altitude", 600)),
                "phasing": int(args.get("phasing", 1)),
                "comms": args.get("comms", "vdes"),
                "weather": args.get("weather", "clear"),
                "res": float(args.get("res", 5)),
                "min_elev": float(args.get("min_elev", 10)),
            }
            if args.get("bidi"):
                payload["bidi"] = True
            # Latency-specific params
            for key in ("from_location", "to_location", "duration", "step", "isl_range", "switching_delay", "architecture"):
                if key in args:
                    payload[key] = args[key]
            if args.get("no_fiber"):
                payload["no_fiber"] = True

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{api}/api/jobs", json=payload, headers=headers)
                if resp.status_code == 202:
                    data = resp.json()
                    return {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": name,
                        "content": json.dumps({
                            "status": "submitted",
                            "job_id": data["job_id"],
                            "mode": mode,
                            "params": payload,
                        }),
                    }
                return await _error_response(tool_call, name, resp)

        elif name == "submit_batch_sweep":
            payload = {
                "mode": args.get("mode", "heatmap"),
                "comms": args.get("comms", "vdes"),
                "sweep_params": args.get("sweep_params", []),
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{api}/api/jobs/batch", json=payload, headers=headers)
                if resp.status_code == 202:
                    data = resp.json()
                    return {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": name,
                        "content": json.dumps({
                            "status": "submitted",
                            "job_id": data["job_id"],
                            "total_combinations": data.get("params", {}).get("total_combinations", "?"),
                        }),
                    }
                return await _error_response(tool_call, name, resp)

        elif name == "get_job_status":
            job_id = args["job_id"]
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{api}/api/jobs/{job_id}", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    summary = {
                        "job_id": data["job_id"],
                        "mode": data["mode"],
                        "status": data["status"],
                        "files": [f["name"] for f in data.get("files", [])],
                    }
                    if data.get("error"):
                        summary["error"] = data["error"]
                    return {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": name,
                        "content": json.dumps(summary),
                    }
                return await _error_response(tool_call, name, resp)

        elif name == "read_csv_data":
            job_id = args["job_id"]
            filename = args["filename"]
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{api}/api/jobs/{job_id}/csv/{filename}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": name,
                        "content": json.dumps(data[:200] if isinstance(data, list) else data),
                    }
                return await _error_response(tool_call, name, resp)

        elif name == "get_simulation_options":
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{api}/api/options", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    summary = {
                        "comms_payloads": data.get("comms_payloads", []),
                        "weather_scenarios": data.get("weather_scenarios", []),
                        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
                        "backends": data.get("backends", []),
                        "constellation_presets": list(data.get("constellation_presets", {}).keys()),
                        "known_constellations": list(data.get("known_constellations", {}).keys()),
                    }
                    return {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": name,
                        "content": json.dumps(summary),
                    }
                return await _error_response(tool_call, name, resp)

        elif name == "upload_file":
            file_id = str(uuid.uuid4())[:8]
            upload_dir = outputs_dir / "_carl_uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            fpath = upload_dir / f"{file_id}_{args['filename']}"
            fpath.write_text(args.get("content", ""), encoding="utf-8")
            return {
                "tool_call_id": tool_call.get("id", ""),
                "name": name,
                "content": json.dumps({
                    "file_id": file_id,
                    "filename": fpath.name,
                    "path": str(fpath),
                }),
            }

        else:
            return {
                "tool_call_id": tool_call.get("id", ""),
                "name": name,
                "content": f"Unknown tool: {name}",
            }

    except httpx.TimeoutException:
        return {
            "tool_call_id": tool_call.get("id", ""),
            "name": name,
            "content": "Error: Request timed out",
        }
    except Exception as e:
        return {
            "tool_call_id": tool_call.get("id", ""),
            "name": name,
            "content": f"Error: {str(e)[:200]}",
        }


async def _error_response(
    tool_call: dict[str, Any], name: str, resp: httpx.Response
) -> dict[str, Any]:
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text[:200]
    return {
        "tool_call_id": tool_call.get("id", ""),
        "name": name,
        "content": json.dumps({"error": f"API {resp.status_code}: {detail}"}),
    }
