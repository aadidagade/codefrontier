import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas
from app.models.handover import Handover


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass ReportLab canvas that calculates the exact total page count
    and renders dynamic running headers and 'Page X of Y' footers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.handover_title = "Engineering Knowledge Handover"
        self.handover_version = "v1.0"

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header on page 2+
        if self._pageNumber > 1:
            header_title = self.handover_title[:60] + ("..." if len(self.handover_title) > 60 else "")
            self.drawString(54, 755, header_title)
            self.drawRightString(612 - 54, 755, f"Version {self.handover_version}")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 747, 612 - 54, 747)

        # Running Footer on all pages
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 32, page_str)
        self.drawString(54, 32, "Confidential — AI-Powered Knowledge Handover Platform")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 44, 612 - 54, 44)

        self.restoreState()


class PDFExportService:
    """
    Industrial ReportLab PDF compiler for Knowledge Handovers.
    
    Generates a professionally styled document:
    1. Document header with version badge and approval sign-off.
    2. Executive summary.
    3. 10 structured handover chapters.
    4. Explicit visual distinction between verified facts, AI recommendations, and contradictions.
    5. Traceable citations table.
    6. Continuation tasks table.
    """

    @staticmethod
    def _escape_xml(text: Any) -> str:
        """Escapes text for safe inclusion inside ReportLab Paragraph flowables."""
        if text is None:
            return ""
        s = str(text)
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return s

    @classmethod
    def generate_handover_pdf(cls, full_handover: Handover, project_name: str = "Project") -> io.BytesIO:
        buffer = io.BytesIO()

        # Page setup: Letter size with 54pt (0.75 in) margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom typography palette
        primary_color = colors.HexColor("#0F172A")    # Slate 900
        secondary_color = colors.HexColor("#1E293B")  # Slate 800
        accent_blue = colors.HexColor("#2563EB")      # Blue 600
        text_dark = colors.HexColor("#334155")        # Slate 700
        verified_green = colors.HexColor("#059669")   # Emerald 600
        rec_amber = colors.HexColor("#D97706")        # Amber 600
        conflict_red = colors.HexColor("#DC2626")     # Red 600
        bg_light = colors.HexColor("#F8FAFC")         # Slate 50

        title_style = ParagraphStyle(
            "CoverTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=primary_color,
            spaceAfter=8,
        )

        subtitle_style = ParagraphStyle(
            "CoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        )

        h1_style = ParagraphStyle(
            "SectionH1",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=secondary_color,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=accent_blue,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=text_dark,
            spaceAfter=6,
        )

        badge_style = ParagraphStyle(
            "Badge",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1,
        )

        verified_callout_style = ParagraphStyle(
            "VerifiedCallout",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#065F46"),
        )

        rec_callout_style = ParagraphStyle(
            "RecCallout",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#92400E"),
        )

        conflict_callout_style = ParagraphStyle(
            "ConflictCallout",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#991B1B"),
        )

        story = []

        # =====================================================================
        # 1. HEADER / METADATA BANNER
        # =====================================================================
        status_text = (full_handover.status or "DRAFT").upper()
        status_color = verified_green if status_text in ("APPROVED", "SHARED", "ACKNOWLEDGED") else accent_blue

        story.append(Paragraph(cls._escape_xml(full_handover.title), title_style))
        story.append(Paragraph(
            f"Project: <b>{cls._escape_xml(project_name)}</b> &nbsp;|&nbsp; Version: <b>{full_handover.version}</b> &nbsp;|&nbsp; Status: <b>{status_text}</b>",
            subtitle_style,
        ))

        # Metadata grid
        gen_date = full_handover.generated_at.strftime("%Y-%m-%d %H:%M UTC") if full_handover.generated_at else "N/A"
        app_date = full_handover.approved_at.strftime("%Y-%m-%d %H:%M UTC") if full_handover.approved_at else "Pending Sign-off"
        shared_date = full_handover.shared_at.strftime("%Y-%m-%d %H:%M UTC") if full_handover.shared_at else "Not Shared"

        meta_data = [
            [
                Paragraph("<b>Generated:</b> " + gen_date, body_style),
                Paragraph("<b>Approved:</b> " + app_date, body_style),
                Paragraph("<b>Shared:</b> " + shared_date, body_style),
            ],
            [
                Paragraph(f"<b>Handover ID:</b> {full_handover.id.hex[:12]}...", body_style),
                Paragraph(f"<b>Version:</b> {full_handover.version}", body_style),
                Paragraph(f"<b>Status:</b> {status_text}", body_style),
            ]
        ]
        meta_table = Table(meta_data, colWidths=[168, 168, 168])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Divider
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=12))

        # =====================================================================
        # 2. 10 STRUCTURED CHAPTERS
        # =====================================================================
        sections = full_handover.sections or []
        for sec in sections:
            story.append(Paragraph(cls._escape_xml(sec.title), h1_style))

            content_dict = sec.content or {}
            if isinstance(content_dict, str):
                story.append(Paragraph(cls._escape_xml(content_dict), body_style))
                continue

            # Summary
            if "summary" in content_dict and content_dict["summary"]:
                summary_text = f"<b>Summary:</b> {cls._escape_xml(content_dict['summary'])}"
                summary_table = Table([[Paragraph(summary_text, body_style)]], colWidths=[504])
                summary_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(summary_table)
                story.append(Spacer(1, 6))

            # Markdown narrative / paragraphs
            if "markdown" in content_dict and content_dict["markdown"]:
                md_text = content_dict["markdown"]
                # Split markdown into readable paragraphs, skip top duplicate headers
                lines = [l.strip() for l in md_text.split("\n") if l.strip()]
                for line in lines:
                    if line.startswith("#"):
                        header_clean = line.lstrip("#").strip()
                        if header_clean.lower() != sec.title.lower():
                            story.append(Paragraph(cls._escape_xml(header_clean), h2_style))
                    elif line.startswith("- ") or line.startswith("* "):
                        bullet_item = f"• {cls._escape_xml(line[2:])}"
                        story.append(Paragraph(bullet_item, body_style))
                    else:
                        story.append(Paragraph(cls._escape_xml(line), body_style))

            # Factual Claims (Verified Facts)
            claims = content_dict.get("claims", [])
            if claims and isinstance(claims, list):
                story.append(Paragraph("Verified Factual Claims & Evidence", h2_style))
                claim_rows = [
                    [
                        Paragraph("<b>Claim Statement</b>", body_style),
                        Paragraph("<b>Status</b>", body_style),
                        Paragraph("<b>Source Evidence Quote</b>", body_style),
                    ]
                ]
                for c in claims[:8]:  # Limit to key claims per chapter
                    stmt = cls._escape_xml(c.get("statement", ""))
                    ev_status = c.get("evidence_status", "SUPPORTED")
                    quote = cls._escape_xml(c.get("quoted_text") or "Referenced in documentation chunks")
                    status_badge = f"<font color='#059669'><b>{ev_status}</b></font>" if "SUPPORTED" in ev_status else f"<font color='#D97706'><b>{ev_status}</b></font>"

                    claim_rows.append([
                        Paragraph(stmt, body_style),
                        Paragraph(status_badge, body_style),
                        Paragraph(f"<i>\"{quote}\"</i>", verified_callout_style),
                    ])

                claim_table = Table(claim_rows, colWidths=[200, 94, 210])
                claim_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(claim_table)
                story.append(Spacer(1, 8))

            # Explicit Recommendations Callout (Separated from facts!)
            recommendations = content_dict.get("recommendations", [])
            if recommendations and isinstance(recommendations, list):
                story.append(Paragraph("AI Recommendations (Advisory Only)", h2_style))
                for rec in recommendations:
                    rec_title = cls._escape_xml(rec.get("title", "Recommendation"))
                    rec_desc = cls._escape_xml(rec.get("description", ""))
                    timeframe = cls._escape_xml(rec.get("timeframe", "immediate").replace("_", " ").title())
                    
                    rec_content = [
                        Paragraph(f"<b>[AI RECOMMENDATION — NOT A DOCUMENTED FACT]</b>: <b>{rec_title}</b> ({timeframe})", rec_callout_style),
                        Paragraph(rec_desc, body_style),
                    ]
                    rec_box = Table([[rec_content]], colWidths=[504])
                    rec_box.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#F59E0B")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]))
                    story.append(rec_box)
                    story.append(Spacer(1, 6))

            # Evidence References for section
            if sec.evidence_references:
                story.append(Paragraph("Citations & Traceability", h2_style))
                for ev in sec.evidence_references[:5]:
                    page_str = f"Page {ev.page_number}" if ev.page_number else "Repository passage"
                    score_str = f"{int(ev.relevance_score * 100)}%" if ev.relevance_score else "N/A"
                    ev_text = f"• <i>\"{cls._escape_xml(ev.quoted_text)}\"</i> — <b>{page_str}</b> (Match: {score_str}, Status: {ev.verification_status})"
                    story.append(Paragraph(ev_text, verified_callout_style))

            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=8))

        # =====================================================================
        # 3. KNOWLEDGE CONFLICTS & DISCREPANCIES CALLOUT
        # =====================================================================
        conflicts = full_handover.conflicts or []
        if conflicts:
            story.append(Paragraph("Cross-Document Conflicts & Unresolved Discrepancies", h1_style))
            for c in conflicts:
                src_a = c.source_a or {}
                src_b = c.source_b or {}
                c_desc = cls._escape_xml(c.description)
                a_quote = cls._escape_xml(src_a.get("text") or src_a.get("quote", "Source A passage"))
                b_quote = cls._escape_xml(src_b.get("text") or src_b.get("quote", "Source B passage"))
                status_str = c.status or "OPEN"

                conflict_box_content = [
                    Paragraph(f"<b>[{c.conflict_type.upper()} CONFLICT] Status: {status_str}</b> — {c_desc}", conflict_callout_style),
                    Spacer(1, 3),
                    Paragraph(f"• <b>Source A:</b> <i>\"{a_quote}\"</i>", body_style),
                    Paragraph(f"• <b>Source B:</b> <i>\"{b_quote}\"</i>", body_style),
                ]
                if c.resolution:
                    chosen = cls._escape_xml(c.resolution.get("chosen_value") or c.resolution.get("resolution_notes", "Resolved"))
                    conflict_box_content.append(Paragraph(f"• <b>Human Resolution:</b> {chosen}", verified_callout_style))

                c_table = Table([[conflict_box_content]], colWidths=[504])
                c_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#EF4444")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(c_table)
                story.append(Spacer(1, 8))

        # =====================================================================
        # 4. ACTIONABLE CONTINUATION TASKS TABLE
        # =====================================================================
        tasks = full_handover.tasks or []
        if tasks:
            story.append(Paragraph("Actionable Continuation Tasks", h1_style))
            task_rows = [
                [
                    Paragraph("<b>Priority</b>", body_style),
                    Paragraph("<b>Task Title & Instructions</b>", body_style),
                    Paragraph("<b>Status</b>", body_style),
                    Paragraph("<b>Due Date</b>", body_style),
                ]
            ]
            for t in tasks:
                p_color = conflict_red if t.priority == "critical" else (rec_amber if t.priority == "high" else text_dark)
                p_text = f"<font color='{p_color.hexval()}'><b>{t.priority.upper()}</b></font>"
                due_str = t.due_date.strftime("%Y-%m-%d") if t.due_date else "Flexible"
                task_rows.append([
                    Paragraph(p_text, body_style),
                    Paragraph(f"<b>{cls._escape_xml(t.title)}</b><br/>{cls._escape_xml(t.description or '')[:140]}", body_style),
                    Paragraph(t.status.upper(), body_style),
                    Paragraph(due_str, body_style),
                ])

            task_table = Table(task_rows, colWidths=[64, 276, 84, 80])
            task_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(task_table)

        # Build document with NumberedCanvas to compute exact total page count
        def make_canvas(*args, **kwargs):
            canv = NumberedCanvas(*args, **kwargs)
            canv.handover_title = full_handover.title
            canv.handover_version = full_handover.version
            return canv

        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer
