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
        return {
            "mean_coverage_pct": 0.0,
            "max_coverage_pct": 0.0,
            "min_coverage_pct": 0.0,
            "coverage_above_90_pct": 0.0,
            "coverage_above_50_pct": 0.0,
        }
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
    fieldnames = (
        ["config", "status"]
        + param_cols
        + [
            "mean_coverage_pct",
            "max_coverage_pct",
            "min_coverage_pct",
            "coverage_above_90_pct",
            "coverage_above_50_pct",
        ]
    )
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
            writer.writerow({"config": r["label"], "status": "OK", **r["params"], **metrics})
    return output_path


def generate_summary_json(results: list[dict[str, Any]], output_path: Path) -> Path:
    """Generate JSON summary for frontend consumption."""
    summary = []
    for r in results:
        entry = {"label": r["label"], "params": r["params"], "success": r["success"], "heatmap_png": str(r.get("heatmap_png", "")) if r.get("heatmap_png") else None}
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


def generate_heatmap_grid(
    results: list[dict[str, Any]], output_path: Path, grid_cols: int = 4
) -> Path:
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
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
        )
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
