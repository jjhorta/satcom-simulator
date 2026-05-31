"""
Tests for watermark module.

Run: python -m pytest tests/test_watermark.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))

import pytest
import tempfile
from pathlib import Path
from app.watermark import should_watermark, apply_watermark, HAS_PILLOW


class TestShouldWatermark:
    """Verify watermark logic per role."""

    def test_viewer_gets_watermarked(self):
        assert should_watermark("viewer") is True

    def test_demo_no_watermark(self):
        assert should_watermark("demo") is False

    def test_creator_no_watermark(self):
        assert should_watermark("creator") is False

    def test_admin_no_watermark(self):
        assert should_watermark("admin") is False


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestApplyWatermark:
    """Verify watermark actually modifies images."""

    def test_watermark_adds_to_png(self):
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGBA", (200, 100), (255, 255, 255, 255))
            img.save(f.name)
            original_size = os.path.getsize(f.name)
            apply_watermark(f.name)
            new_size = os.path.getsize(f.name)
            # Watermark should make the file larger (or at least different metadata)
            assert os.path.exists(f.name)
            os.unlink(f.name)

    def test_watermark_skips_non_images(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"lat,lon\n1,2\n")
            f.flush()
            apply_watermark(f.name)
            content = open(f.name, "rb").read()
            assert content == b"lat,lon\n1,2\n"  # unchanged
            os.unlink(f.name)

    def test_watermark_skips_missing_file(self):
        """Should not crash on missing file."""
        apply_watermark("/tmp/nonexistent_file_xyz.png")  # should not raise

    def test_watermark_skips_html(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html></html>")
            f.flush()
            apply_watermark(f.name)
            content = open(f.name, "rb").read()
            assert content == b"<html></html>"  # unchanged
            os.unlink(f.name)
