"""
generate_report.py — builds a branded PDF foot-traffic report for Saarde.

Reads the most recent entries from foot_traffic_log.csv (written by
humandetector.py each time it finishes processing footage) and produces a
one-page PDF summarising total traffic, daily average, and the highest and
lowest traffic days over that window — then opens it.
"""

import csv
import os
import platform
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SCRIPT_DIR = Path(__file__).parent
LOG_PATH   = SCRIPT_DIR / "foot_traffic_log.csv"
LOGO_PATH  = SCRIPT_DIR / "saarde-logo-LIS.png"
DAYS_SHOWN = 7  # last 7 log entries, including today if present

# ── Palette — black ink on white, matching the Saarde wordmark ────────────────
INK   = "#111111"
MUTED = "#6b6b6b"
LINE  = colors.HexColor("#111111")
ROWBG = colors.HexColor("#f6f5f2")


# ── Data ───────────────────────────────────────────────────────────────────
def load_entries(log_path: Path, n: int) -> list[tuple[date, int]]:
    if not log_path.exists():
        sys.exit(f"No log file found at {log_path}.\nRun humandetector.py first to record some foot traffic.")

    rows: list[tuple[date, int]] = []
    with open(log_path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                rows.append((date.fromisoformat(row["date"]), int(row["count"])))
            except (KeyError, ValueError, TypeError):
                continue

    if not rows:
        sys.exit(f"{log_path} has no valid date,count rows.")

    rows.sort(key=lambda r: r[0])
    return rows[-n:]


def format_range(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{start.day}–{end.day} {end.strftime('%B %Y')}"
    if start.year == end.year:
        return f"{start.strftime('%d %B')} – {end.strftime('%d %B %Y')}"
    return f"{start.strftime('%d %B %Y')} – {end.strftime('%d %B %Y')}"


# ── PDF helpers ────────────────────────────────────────────────────────────
def tracked(text: str) -> str:
    """Adds letter-spacing to a caps label for a more editorial look.

    Uses non-breaking spaces because reportlab's paragraph parser collapses
    runs of plain ASCII spaces (HTML-style), which would otherwise erase the
    gaps between words.
    """
    words = text.upper().split(" ")
    return "   ".join(" ".join(w) for w in words)


def kpi_card(label: str, value: str, sub: str = "") -> Paragraph:
    style = ParagraphStyle("kpi", alignment=TA_CENTER, leading=14)
    html = (
        f'<font name="Helvetica" size="7.5" color="{MUTED}">{tracked(label)}</font>'
        f'<br/><br/>'
        f'<font name="Times-Bold" size="27" color="{INK}">{value}</font>'
    )
    if sub:
        html += f'<br/><font name="Helvetica" size="8.5" color="{MUTED}">{sub}</font>'
    else:
        html += '<br/><font size="8.5"> </font>'
    return Paragraph(html, style)


def build_pdf(entries: list[tuple[date, int]], out_path: Path) -> None:
    counts       = [c for _, c in entries]
    total        = sum(counts)
    average      = total / len(entries)
    highest_day  = max(entries, key=lambda r: r[1])
    lowest_day   = min(entries, key=lambda r: r[1])
    range_label  = format_range(entries[0][0], entries[-1][0])

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title="Saarde Foot Traffic Report",
    )
    avail_width = doc.width
    story = []

    # ── Header: logo + title/subtitle ─────────────────────────────────────
    logo_w = 42 * mm
    logo_h = logo_w * (ImageReader(str(LOGO_PATH)).getSize()[1] / ImageReader(str(LOGO_PATH)).getSize()[0])
    logo = Image(str(LOGO_PATH), width=logo_w, height=logo_h)

    title_style = ParagraphStyle("title", alignment=TA_RIGHT, fontName="Times-Bold",
                                  fontSize=18, textColor=colors.HexColor(INK), leading=22)
    subtitle_style = ParagraphStyle("subtitle", alignment=TA_RIGHT, fontName="Helvetica",
                                     fontSize=10.5, textColor=colors.HexColor(MUTED), leading=14,
                                     spaceBefore=2)
    header_text = Paragraph(
        f'{tracked("Foot Traffic Report")}<br/><font size="10.5">{range_label}</font>',
        title_style,
    )

    header = Table([[logo, header_text]], colWidths=[logo_w, avail_width - logo_w])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header)
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=8 * mm))

    # ── KPI row ──────────────────────────────────────────────────────────
    cards = [
        kpi_card("Total Traffic", f"{total:,}"),
        kpi_card("Average Daily", f"{average:,.1f}"),
        kpi_card("Highest Day", f"{highest_day[1]:,}", highest_day[0].strftime("%a %d %b")),
        kpi_card("Lowest Day", f"{lowest_day[1]:,}", lowest_day[0].strftime("%a %d %b")),
    ]
    kpi_table = Table([cards], colWidths=[avail_width / 4] * 4)
    kpi_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.6, colors.HexColor("#d9d8d4")),
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, LINE),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12 * mm))

    # ── Daily breakdown ──────────────────────────────────────────────────
    section_style = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=9,
                                    textColor=colors.HexColor(INK), spaceAfter=6)
    story.append(Paragraph(tracked("Daily Breakdown"), section_style))

    header_row = ["DATE", "DAY", "FOOT TRAFFIC"]
    body_rows = [
        [d.strftime("%d %b %Y"), d.strftime("%A"), f"{c:,}"]
        for d, c in entries
    ]
    table_data = [header_row] + body_rows
    breakdown = Table(table_data, colWidths=[avail_width * 0.32, avail_width * 0.38, avail_width * 0.30])
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(MUTED)),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor(INK)),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, LINE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (0, -1), 2),
    ]
    for i, (d, c) in enumerate(entries, start=1):
        if d in (highest_day[0], lowest_day[0]):
            style.append(("TEXTCOLOR", (0, i), (-1, i), colors.HexColor(INK)))
            style.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ROWBG))
    breakdown.setStyle(TableStyle(style))
    story.append(breakdown)
    story.append(Spacer(1, 14 * mm))

    # ── Footer ───────────────────────────────────────────────────────────
    footer_style = ParagraphStyle("footer", alignment=TA_CENTER, fontName="Helvetica",
                                   fontSize=7.5, textColor=colors.HexColor(MUTED))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d9d8d4"), spaceAfter=4 * mm))
    story.append(Paragraph(
        f"Generated automatically by the Saarde Foot Traffic Tracker — "
        f"{datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        footer_style,
    ))

    doc.build(story)


def open_file(path: Path) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as e:
        print(f"Could not auto-open the PDF ({e}). Find it at: {path}")


def main() -> None:
    entries = load_entries(LOG_PATH, DAYS_SHOWN)
    if len(entries) < DAYS_SHOWN:
        print(f"Note: only {len(entries)} day(s) logged so far — report covers what's available.")

    range_label = format_range(entries[0][0], entries[-1][0]).replace(" ", "_").replace("–", "to")
    out_path = SCRIPT_DIR / f"foot_traffic_report_{range_label}.pdf"

    build_pdf(entries, out_path)
    print(f"Report saved to {out_path}")
    open_file(out_path)


if __name__ == "__main__":
    main()
