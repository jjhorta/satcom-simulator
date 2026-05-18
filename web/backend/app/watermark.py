"""
web/backend/app/watermark.py — Watermark overlay for free-tier exports.

The watermark is applied AFTER the simulator generates the image,
by post-processing the PNG output file.

Approach: Use Pillow to overlay semi-transparent diagonal text.
Works on PNG files. Skips non-image files (CSV, GIF, HTML, JSON, TXT).

The worker calls should_watermark(tier) + apply_watermark(filepath)
after each simulation job completes.
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

WATERMARK_TEXT = "Constellation Simulator · Free Tier"
WATERMARK_OPACITY: int = 80  # 0-255 (lower = more transparent)


def should_watermark(role: str) -> bool:
    """Only watermark free tier (viewer role) outputs."""
    return role == "viewer"


def apply_watermark(filepath: str | Path) -> None:
    """Apply a diagonal watermark to the given image file.

    Works on PNG/JPEG images. Skips non-image files.
    Does nothing silently if Pillow is not installed.
    """
    if not HAS_PILLOW:
        return

    ext = os.path.splitext(str(filepath))[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        return  # skip non-image files

    try:
        img = Image.open(filepath).convert("RGBA")
    except Exception:
        return  # corrupt or unreadable image

    # Create a transparent overlay
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load a font; fall back to default
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36
        )
    except (IOError, OSError):
        try:
            # Fallback to any available bold font
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36
            )
        except (IOError, OSError):
            font = ImageFont.load_default()

    # Calculate text dimensions
    text = WATERMARK_TEXT
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Repeat diagonally for full coverage
    step_x = text_w + 120
    step_y = text_h + 120

    for y in range(-text_h, img.height + text_h, step_y):
        for x in range(-text_w, img.width + text_w, step_x):
            draw.text(
                (x, y),
                text,
                font=font,
                fill=(128, 128, 128, WATERMARK_OPACITY),
            )

    # Composite and save (convert back to RGB for JPEG compatibility)
    watermarked = Image.alpha_composite(img, overlay)
    watermarked.convert("RGB").save(str(filepath), "PNG")
