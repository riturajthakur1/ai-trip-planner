"""
Bespoke PDF Itinerary Generator for Curated India Travel Planner.
Uses ReportLab to generate elegant, publication-quality travel dossiers for end travelers.
"""

import io
import re
from typing import Optional, List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from agent.state import GeneratedItinerary, DayPlan
from data.db import TravelDatabase


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count in footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        page_w, page_h = A4

        # Top subtle running header (on page 2 onwards)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 7)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(36, page_h - 26, "BESPOKE INDIA TRAVEL DOSSIER")
            self.setFont("Helvetica", 7)
            self.drawRightString(page_w - 36, page_h - 26, "GROUNDED CATALOG INVENTORY")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, page_h - 30, page_w - 36, page_h - 30)

        # Bottom Running Footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 36, page_w - 36, 36)

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(36, 24, "Curated India AI Trip Planner  |  Private & Confidential Itinerary")

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_w - 36, 24, page_str)

        self.restoreState()


def clean_text(text: str) -> str:
    """Sanitize markdown and unicode emojis to ensure crisp, error-free rendering in standard PDF fonts."""
    if not text:
        return ""

    # Common emoji mappings to clean textual labels or bullets
    replacements = {
        "🌿": "",
        "🏰": "",
        "🏔️": "",
        "🛶": "",
        "🌴": "",
        "🌌": "",
        "🎨": "",
        "☁️": "",
        "🏛️": "",
        "🌅": "",
        "☀️": "",
        "🌇": "",
        "🍽️": "",
        "💡": "",
        "🏡": "",
        "📍": "",
        "🚗": "",
        "👫": "",
        "👨‍👩‍👧": "",
        "🎒": "",
        "👥": "",
        "🌸": "",
        "⚖️": "",
        "🥾": "",
        "👑": "",
        "💰": "",
        "✨": "",
        "☕": "",
        "🌊": "",
        "🧘": "",
        "🛍️": "",
        "🗺️": "",
        "📥": "",
        "⚡": "",
        "✅": "",
        "🙏": "",
        "₹": "Rs. ",
    }
    for emoji_char, clean_val in replacements.items():
        text = text.replace(emoji_char, clean_val)

    # Remove any remaining raw unicode astral emojis
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)

    # Clean double spaces
    text = re.sub(r" +", " ", text).strip()
    return text


def build_pdf_itinerary(itinerary: GeneratedItinerary, circuit_id: Optional[str] = None) -> bytes:
    """Generate a clean, high-design travel PDF from a GeneratedItinerary object."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    # Brand Colors
    c_primary = colors.HexColor("#0F172A")    # Deep Navy
    c_brand = colors.HexColor("#0F766E")      # Deep Emerald / Teal
    c_dark = colors.HexColor("#1E293B")       # Slate 800
    c_muted = colors.HexColor("#64748B")      # Slate 500
    c_bg_light = colors.HexColor("#F8FAFC")   # Slate 50
    c_border = colors.HexColor("#E2E8F0")     # Slate 200
    c_accent_bg = colors.HexColor("#F0FDFA")  # Teal 50
    c_gold = colors.HexColor("#B45309")       # Amber 700

    # Custom Typography Styles
    style_header_super = ParagraphStyle(
        "HeaderSuper",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=c_brand,
        alignment=TA_LEFT,
        textTransform="uppercase",
        spaceAfter=4,
    )

    style_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=c_primary,
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    style_tagline = ParagraphStyle(
        "DocTagline",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=15,
        textColor=c_muted,
        alignment=TA_LEFT,
        spaceAfter=14,
    )

    style_section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
    )

    style_day_title = ParagraphStyle(
        "DayTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=c_primary,
    )

    style_day_stay = ParagraphStyle(
        "DayStay",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=c_brand,
    )

    style_body = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=3,
    )

    style_body_bold_prefix = ParagraphStyle(
        "BodyBoldPrefix",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=4,
    )

    style_tip = ParagraphStyle(
        "TipText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E3A8A"),  # Blue 900
    )

    style_grid_label = ParagraphStyle(
        "GridLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=c_muted,
        textTransform="uppercase",
    )

    style_grid_val = ParagraphStyle(
        "GridVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=c_primary,
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("BESPOKE CURATED TRAVEL DOSSIER • INDIA", style_header_super))
    story.append(Paragraph(clean_text(itinerary.circuit_name), style_title))
    story.append(Paragraph(f'"{clean_text(itinerary.tagline)}"', style_tagline))

    # 2. Key Specs Grid Table
    col_width = (A4[0] - 72) / 4.0
    budget_label = "BUDGET CAP"
    budget_val = f"Rs. {itinerary.max_budget_inr:,}" if itinerary.max_budget_inr else "Curated Value"
    if itinerary.estimated_total_cost_inr:
        budget_val += f" (Est: Rs. {itinerary.estimated_total_cost_inr:,})"

    overview_data = [
        [
            Paragraph("DURATION", style_grid_label),
            Paragraph("TRAVELER PROFILE", style_grid_label),
            Paragraph("PLANNED PACE", style_grid_label),
            Paragraph(budget_label, style_grid_label),
        ],
        [
            Paragraph(f"{itinerary.total_days} Days", style_grid_val),
            Paragraph(clean_text(itinerary.traveler_profile), style_grid_val),
            Paragraph(clean_text(itinerary.pace).title(), style_grid_val),
            Paragraph(clean_text(budget_val), style_grid_val),
        ],
    ]
    overview_table = Table(overview_data, colWidths=[col_width] * 4)
    overview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), c_bg_light),
                ("BOX", (0, 0), (-1, -1), 0.75, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(overview_table)
    story.append(Spacer(1, 12))

    # 3. Why Personalized / Philosophy Note
    if itinerary.why_personalized:
        why_text = f"<b>Curator's Note:</b> {clean_text(itinerary.why_personalized)}"
        why_table = Table([[Paragraph(why_text, style_body)]], colWidths=[A4[0] - 72])
        why_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), c_accent_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#99F6E4")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(why_table)
        story.append(Spacer(1, 10))

    # 4. Handpicked Stays Summary
    story.append(Paragraph("Handpicked Signature Accommodations", style_section_heading))
    stay_headers = [
        Paragraph("<b>Property Name</b>", style_grid_label),
        Paragraph("<b>Setting / Hub</b>", style_grid_label),
        Paragraph("<b>Character & Experience</b>", style_grid_label),
        Paragraph("<b>Nightly Rate</b>", style_grid_label),
    ]
    stay_rows = [stay_headers]
    for stay in itinerary.stays_summary:
        s_name = stay.get("stay_name") or stay.get("name", "")
        s_hub = stay.get("hub") or stay.get("location", "")
        s_why = stay.get("why_special") or stay.get("vibe", "")
        s_price = stay.get("price_approx", "")
        f_tag = "Food: Yes" if stay.get("food_available", True) else "Food: No"
        b_tag = "Bfast: Included" if stay.get("breakfast_available", True) else "Bfast: No"
        w_tag = "WiFi: Yes" if stay.get("wifi_available", True) else "WiFi: No"
        s_desc = f"{s_why}<br/><font color='#047857'><b>[{f_tag} • {b_tag} • {w_tag}]</b></font>"
        stay_rows.append(
            [
                Paragraph(f"<b>{clean_text(s_name)}</b>", style_body),
                Paragraph(clean_text(s_hub), style_body),
                Paragraph(clean_text(s_desc), style_body),
                Paragraph(clean_text(s_price), style_body),
            ]
        )
    table_w = A4[0] - 72
    stays_table = Table(stay_rows, colWidths=[table_w * 0.28, table_w * 0.18, table_w * 0.38, table_w * 0.16])
    stays_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.75, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(stays_table)
    story.append(Spacer(1, 12))

    # 5. Day-by-Day Detailed Itinerary
    story.append(Paragraph("Detailed Day-by-Day Journey", style_section_heading))

    for day in itinerary.days:
        day_elements = []

        # Day Banner Table
        day_title_text = f"Day {day.day_number}: {clean_text(day.destination)} — {clean_text(day.theme)}"
        day_stay_text = f"Overnight: {clean_text(day.stay_name)}"
        banner_data = [
            [
                Paragraph(day_title_text, style_day_title),
                Paragraph(day_stay_text, style_day_stay),
            ]
        ]
        banner_table = Table(banner_data, colWidths=[table_w * 0.65, table_w * 0.35])
        banner_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ]
            )
        )
        day_elements.append(banner_table)
        day_elements.append(Spacer(1, 5))

        # Schedule Details
        details_flow = []
        if day.morning_activity:
            details_flow.append(
                Paragraph(f"<b>Morning:</b> {clean_text(day.morning_activity)}", style_body_bold_prefix)
            )
        if day.afternoon_activity:
            details_flow.append(
                Paragraph(f"<b>Afternoon:</b> {clean_text(day.afternoon_activity)}", style_body_bold_prefix)
            )
        if day.sunset_evening_activity:
            details_flow.append(
                Paragraph(f"<b>Evening:</b> {clean_text(day.sunset_evening_activity)}", style_body_bold_prefix)
            )
        if day.dining_highlight:
            details_flow.append(
                Paragraph(f"<b>Dining Highlight:</b> {clean_text(day.dining_highlight)}", style_body_bold_prefix)
            )

        # Insider Tip Callout
        if day.insider_advice:
            tip_content = f"<b>Insider Advice:</b> {clean_text(day.insider_advice)}"
            tip_table = Table([[Paragraph(tip_content, style_tip)]], colWidths=[table_w - 12])
            tip_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),  # Blue 50
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            details_flow.append(tip_table)

        # Wrap schedule in a padded content block
        schedule_table = Table([[d] for d in details_flow], colWidths=[table_w])
        schedule_table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        day_elements.append(schedule_table)
        day_elements.append(Spacer(1, 8))

        # Keep Day unit together if reasonable to avoid awkward mid-day page breaks
        story.append(KeepTogether(day_elements))

    # 6. Logistics & Local Advisory
    db = TravelDatabase.get_instance()
    circuit = db.circuits_by_id.get(circuit_id) if circuit_id else None
    if not circuit:
        for c in db.dataset.circuits:
            if c.circuit_name.lower() in itinerary.circuit_name.lower():
                circuit = c
                break

    if circuit:
        logistics_elements = [
            Spacer(1, 6),
            Paragraph("Circuit Logistics & Practical Travel Notes", style_section_heading),
        ]
        notes = []
        if circuit.best_months:
            notes.append(f"<b>Optimal Months:</b> {', '.join(circuit.best_months)}")
        if circuit.hubs:
            notes.append(f"<b>Transit Hubs & Gateways:</b> {', '.join(circuit.hubs)}")
        if circuit.transfer_logistics:
            transfer_items = [f"<b>{k}:</b> {v}" for k, v in circuit.transfer_logistics.items()]
            notes.append(f"<b>Transfer Logistics:</b><br/>" + "<br/>".join(transfer_items))

        logistics_flow = [Paragraph(n, style_body_bold_prefix) for n in notes]
        log_table = Table([[item] for item in logistics_flow], colWidths=[table_w])
        log_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, c_border),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        logistics_elements.append(log_table)
        story.append(KeepTogether(logistics_elements))

    # Build the document with our NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
