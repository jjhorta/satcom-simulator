"""
PDF Report Generator for Constellation Simulator.

Generates polished PDF reports from simulation results.
"""

import io
import csv
from pathlib import Path
from datetime import datetime


def generate_pdf_report(
    simulation_id: str,
    title: str = "Constellation Analysis Report",
    format: str = "executive",
    csv_data: str | None = None,
    charts: list[str] | None = None,
    maps: list[str] | None = None,
) -> bytes:
    """
    Generate a polished PDF report.

    Args:
        simulation_id: Unique simulation identifier
        title: Report title
        format: 'executive' (1-page summary) or 'technical' (full analysis)
        csv_data: Optional CSV string with simulation data
        charts: Optional list of chart image paths (PNG)
        maps: Optional list of map image paths (PNG)

    Returns:
        PDF content as bytes
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import mm, cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Image, Table,
            TableStyle, PageBreak, KeepTogether,
        )
        from reportlab.lib import colors
    except ImportError:
        # Fallback: generate a minimal HTML report instead
        return _generate_html_report(simulation_id, title, format, csv_data, charts, maps)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=22, spaceAfter=6*mm,
        textColor=HexColor("#1a1a2e"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#666666"),
        spaceAfter=4*mm,
    )
    section_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        fontSize=14, spaceBefore=6*mm, spaceAfter=3*mm,
        textColor=HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, leading=14,
        spaceAfter=2*mm,
    )

    elements = []

    # ── Title page ────────────────────────────────────────────
    elements.append(Spacer(1, 3*cm))
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Simulation: {simulation_id} | Format: {format}",
        subtitle_style
    ))
    elements.append(Spacer(1, 1*cm))

    # ── Executive summary ─────────────────────────────────────
    elements.append(Paragraph("Executive Summary", section_style))
    elements.append(Paragraph(
        "This report presents the results of a satellite constellation simulation "
        "including coverage analysis, IP throughput, and demand-supply matching "
        "for the configured orbital architecture.",
        body_style
    ))

    # ── Maps ──────────────────────────────────────────────────
    if maps:
        elements.append(Paragraph("Coverage Maps", section_style))
        for map_path in maps:
            try:
                img = Image(map_path, width=16*cm, height=9*cm)
                elements.append(img)
                elements.append(Spacer(1, 3*mm))
            except Exception:
                pass

    # ── Charts ────────────────────────────────────────────────
    if charts:
        elements.append(Paragraph("Analysis Charts", section_style))
        for chart_path in charts:
            try:
                img = Image(chart_path, width=14*cm, height=8*cm)
                elements.append(img)
                elements.append(Spacer(1, 3*mm))
            except Exception:
                pass

    # ── Data tables ──────────────────────────────────────────
    if csv_data:
        elements.append(Paragraph("Detailed Data", section_style))
        try:
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)
            if rows:
                # Show first 50 rows as a table
                display_rows = rows[:51]
                table = Table(display_rows, repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#16213e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f8f9fa"), colors.white]),
                ]))
                elements.append(table)
                if len(rows) > 51:
                    elements.append(Paragraph(
                        f"... and {len(rows) - 50} more rows",
                        ParagraphStyle("Note", parent=body_style,
                                       textColor=HexColor("#999999"))
                    ))
        except Exception:
            elements.append(Paragraph("(Data available as CSV download)", body_style))

    # ── Footer ────────────────────────────────────────────────
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "ConstellaSim — Constellation Simulation Platform",
        ParagraphStyle("Footer", parent=body_style,
                       textColor=HexColor("#999999"), fontSize=8,
                       alignment=1)
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def _generate_html_report(
    simulation_id: str,
    title: str,
    format: str,
    csv_data: str | None = None,
    charts: list[str] | None = None,
    maps: list[str] | None = None,
) -> bytes:
    """Fallback HTML report when reportlab is unavailable."""
    html_parts = [
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{title}</title>",
        f"<style>body{{font-family:sans-serif;max-width:900px;margin:auto;padding:20px}}",
        f"h1{{color:#16213e}}h2{{color:#1a1a2e;border-bottom:2px solid #eee}}",
        f"table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:4px 8px}}",
        f"th{{background:#16213e;color:white}}.footer{{color:#999;font-size:0.8em;margin-top:40px}}</style>",
        f"</head><body>",
        f"<h1>{title}</h1>",
        f"<p>Simulation: {simulation_id} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
    ]
    if maps:
        html_parts.append("<h2>Coverage Maps</h2>")
        for m in maps:
            html_parts.append(f"<img src='{m}' style='max-width:100%' />")

    if charts:
        html_parts.append("<h2>Analysis Charts</h2>")
        for c in charts:
            html_parts.append(f"<img src='{c}' style='max-width:80%' />")

    if csv_data:
        html_parts.append("<h2>Data</h2><pre>")
        html_parts.append(csv_data[:5000])
        if len(csv_data) > 5000:
            html_parts.append("\n... (truncated)")
        html_parts.append("</pre>")

    html_parts.append("<p class='footer'>ConstellaSim — Constellation Simulation Platform</p>")
    html_parts.append("</body></html>")
    return "".join(html_parts).encode("utf-8")


def generate_report_from_args(args):
    """CLI entry point for report generation."""
    sim_id = getattr(args, "simulation_id", "unknown")
    title = getattr(args, "title", "Constellation Analysis Report")
    fmt = getattr(args, "format", "executive")

    csv_path = getattr(args, "csv", None)
    csv_data = Path(csv_path).read_text() if csv_path and Path(csv_path).exists() else None

    charts = getattr(args, "charts", [])
    maps = getattr(args, "maps", [])

    pdf = generate_pdf_report(sim_id, title, fmt, csv_data, charts, maps)
    output = getattr(args, "output", f"report_{sim_id}.pdf")
    Path(output).write_bytes(pdf)
    print(f"✅ Report saved: {output} ({len(pdf)} bytes)")
