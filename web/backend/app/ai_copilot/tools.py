"""CARL tool definitions — JSON schemas for LLM function calling."""
from __future__ import annotations

from typing import Any

# ── Tool schemas (OpenAI function-calling format) ─────────────────────────────

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "submit_simulation",
            "description": "Run a constellation simulation job (heatmap, heatmap-rf, orbit, track, route, latency). Returns job_id — poll get_job_status for completion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["heatmap", "heatmap-rf", "orbit", "track", "route", "latency"],
                        "description": "Simulation mode",
                    },
                    "sats": {"type": "integer", "description": "Number of satellites"},
                    "planes": {"type": "integer", "description": "Number of orbital planes"},
                    "inclination": {"type": "number", "description": "Orbital inclination in degrees"},
                    "altitude": {"type": "number", "description": "Orbit altitude in km"},
                    "phasing": {"type": "integer", "description": "Walker phasing factor (default: 1)"},
                    "comms": {
                        "type": "string",
                        "enum": ["ais", "vdes", "mss", "starlink_ku", "gsm", "lte", "5g"],
                        "description": "Communications payload type",
                    },
                    "weather": {
                        "type": "string",
                        "enum": ["clear", "smoke", "drizzle", "rain", "storm", "tropical"],
                        "description": "Weather scenario for RF link budget",
                    },
                    "res": {"type": "number", "description": "Grid resolution in degrees (default: 5)"},
                    "min_elev": {"type": "number", "description": "Minimum elevation angle in degrees (default: 10)"},
                    "bidi": {"type": "boolean", "description": "Bidirectional link calculation"},
                },
                "required": ["mode", "sats", "planes", "inclination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_batch_sweep",
            "description": "Run a parametric sweep over multiple Walker configurations. Useful for comparing many designs overnight.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["heatmap", "heatmap-rf"],
                        "description": "Simulation mode for each combo",
                    },
                    "sweep_params": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "param": {
                                    "type": "string",
                                    "enum": ["sats", "planes", "inclination", "altitude", "phasing", "weather"],
                                },
                                "values": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Values to sweep",
                                },
                            },
                            "required": ["param", "values"],
                        },
                    },
                    "comms": {"type": "string", "description": "Communications payload"},
                },
                "required": ["mode", "sweep_params"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_status",
            "description": "Get the current status and output files of a simulation job. Returns status (queued/running/completed/failed), files list, and error if any.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "The job UUID"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_csv_data",
            "description": "Read a simulation CSV file as structured JSON data. Use this to analyze heatmap coverage, route waypoints, or latency results programmatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "The job UUID"},
                    "filename": {"type": "string", "description": "CSV filename (e.g. heatmap_vdes_walker_53_12_6.csv)"},
                },
                "required": ["job_id", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_simulation_options",
            "description": "List all available simulation options: comms payloads, weather scenarios, locations, routes, platforms, backends, and known constellation presets.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upload_file",
            "description": "Upload a CSV or GeoJSON file for analysis. Provide the file content as text. Returns a file_id you can reference in read_csv_data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Original filename"},
                    "content": {"type": "string", "description": "File content as text"},
                },
                "required": ["filename", "content"],
            },
        },
    },
]
