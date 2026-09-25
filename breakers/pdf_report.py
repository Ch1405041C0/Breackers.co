from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DARK = colors.HexColor("#0B120D")
LIME = colors.HexColor("#C8FF5A")
MUTED = colors.HexColor("#526056")
LINE = colors.HexColor("#D9E1DA")


def _txt(value) -> str:
    return escape(str(value if value not in (None, "") else "—"))


def build_scan_pdf(*, breakers_id: str, created_at: str, report: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title=f"BREAKERS SCAN {breakers_id}",
        author="BREAKERS CO",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("BreakersTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=28, leading=31, textColor=DARK, spaceAfter=6)
    kicker = ParagraphStyle("Kicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=MUTED, spaceAfter=5)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=DARK, spaceBefore=12, spaceAfter=7)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=DARK, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=DARK, spaceAfter=5)
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=11, textColor=MUTED)
    score_style = ParagraphStyle("Score", parent=title, fontSize=34, leading=38, alignment=TA_CENTER)

    status = str(report.get("analysis_status") or "incomplete").upper()
    score = report.get("score") if status == "COMPLETED" else None
    findings = list(report.get("findings") or [])
    source = report.get("source") or {}
    risk_summary = report.get("risk_summary") or {}
    limitations = list(risk_summary.get("limitations") or [])
    for failed in report.get("failed_engines") or []:
        limitations.append(f"{failed.get('engine', 'Análisis')}: {failed.get('error', 'no pudo completarse')}")

    story = [
        Paragraph("BREAKERS <font size='10'>CO</font>", title),
        Paragraph("QUALITY REPORT / SCAN", kicker),
        Spacer(1, 4*mm),
        Paragraph("Informe de calidad", h1),
        Paragraph(f"<b>ID BREAKERS</b><br/>{_txt(breakers_id)}", body),
        Paragraph(f"<b>FECHA</b><br/>{_txt(created_at)}", body),
        Paragraph(f"<b>OBJETIVO ANALIZADO</b><br/>{_txt(report.get('target'))}", body),
        Paragraph(f"<b>ESTADO DEL ANÁLISIS</b><br/>{_txt(status)}", body),
        Spacer(1, 5*mm),
        Paragraph("SCORE", kicker),
        Paragraph("—" if score is None else f"{score} <font size='13'>/ 100</font>", score_style),
        Spacer(1, 3*mm),
        Paragraph("Resumen ejecutivo", h1),
        Paragraph(
            f"BREAKERS registró <b>{len(findings)} hallazgos</b> en los controles ejecutados. "
            "Este informe representa el estado observado durante esta intervención y no debe interpretarse automáticamente como el estado actual del proyecto.",
            body,
        ),
        Paragraph("Qué se analizó", h1),
        Paragraph(f"<b>Tipo de entrada:</b> {_txt(source.get('type'))}", body),
    ]
    if source.get("commit_sha"):
        story.append(Paragraph(f"<b>Commit analizado:</b> {_txt(source.get('commit_sha'))}", body))

    performed = report.get("engines") or []
    unavailable = report.get("unavailable_engines") or []
    story += [
        Paragraph("Cobertura y limitaciones", h1),
        Paragraph(f"<b>Cobertura completada:</b> {_txt(', '.join(performed) if performed else 'No registrada')}", body),
        Paragraph(f"<b>Cobertura no disponible:</b> {_txt(', '.join(unavailable) if unavailable else 'Ninguna registrada')}", body),
    ]
    if limitations:
        for item in limitations:
            story.append(Paragraph(f"• {_txt(item)}", body))
    else:
        story.append(Paragraph("No se registraron limitaciones adicionales.", body))

    story += [PageBreak(), Paragraph("Hallazgos", h1)]
    if not findings:
        story.append(Paragraph("No se registraron hallazgos en los controles que pudieron completarse.", body))

    for index, item in enumerate(findings, 1):
        priority = str(item.get("severity") or "UNKNOWN").upper()
        story.append(Paragraph(f"HALLAZGO {index:02d} / {priority}", kicker))
        story.append(Paragraph(_txt(item.get("title") or "Hallazgo"), h2))
        rows = [
            ["ÁREA", _txt(item.get("category") or "quality")],
            ["UBICACIÓN / EVIDENCIA", _txt(item.get("evidence") or "No registrada")],
            ["RIESGO", _txt(item.get("title") or "Hallazgo detectado")],
            ["PRIORIDAD", _txt(priority)],
            ["ACCIÓN RECOMENDADA", "Revisar y validar el hallazgo en el contexto actual antes de aplicar cambios."],
        ]
        table = Table([[Paragraph(f"<b>{a}</b>", small), Paragraph(b, body)] for a,b in rows], colWidths=[43*mm, 120*mm], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LINEBELOW", (0,0), (-1,-1), 0.35, LINE),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story += [table, Spacer(1, 5*mm)]

    story += [
        Paragraph("Alcance del informe", h1),
        Paragraph(
            "Este documento conserva el resultado de la observación realizada por BREAKERS. "
            "La evidencia reproducible durante la intervención puede depender de artefactos fuente que no se conservan de forma permanente. "
            "La ausencia de un hallazgo no demuestra por sí sola la ausencia de riesgo fuera de la cobertura efectivamente ejecutada.",
            small,
        ),
    ]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18*mm, 12*mm, A4[0]-18*mm, 12*mm)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(DARK)
        canvas.drawString(18*mm, 7.5*mm, "BREAKERS CO / QUALITY REPORT")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(A4[0]-18*mm, 7.5*mm, f"{breakers_id} · {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
