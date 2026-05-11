"""
Export analysis results to PDF (reportlab) and CSV (csv stdlib).
"""
import csv
import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------

def export_results_csv(results: Dict[str, Any]) -> bytes:
    """Flatten the results object into a CSV bytes blob."""
    buffer = io.StringIO()
    w = csv.writer(buffer)

    sentiment = results.get("sentiment_summary") or {}
    metrics = results.get("metrics") or {}

    w.writerow(["Section", "Key", "Value"])
    w.writerow(["meta", "total_reviews", metrics.get("total_reviews", "")])
    w.writerow(["meta", "primary_language", metrics.get("primary_language", "")])
    w.writerow(["meta", "analyses_performed", ",".join(metrics.get("analyses_performed", []))])
    w.writerow(["meta", "duration_ms", metrics.get("duration_ms", "")])

    if sentiment:
        for k in ("total", "positive", "negative", "positive_percent", "negative_percent"):
            w.writerow(["sentiment", k, sentiment.get(k, "")])

    aspects = results.get("aspects") or {}
    if aspects.get("aspects"):
        w.writerow([])
        w.writerow(["Aspect", "Mentions", "Positive", "Negative", "Neutral", "Pos%", "Neg%", "Polarity"])
        for a in aspects["aspects"]:
            w.writerow([
                a["aspect"], a["total_mentions"], a["positive"], a["negative"],
                a["neutral"], a["positive_pct"], a["negative_pct"], a["polarity"],
            ])

    topics = results.get("topics") or {}
    if topics.get("topics"):
        w.writerow([])
        w.writerow(["Topic", "Count", "Keywords"])
        for idx, t in enumerate(topics["topics"], start=1):
            kw = ", ".join(t.get("keywords", []))
            w.writerow([t.get("id", t.get("topic_id", idx)), t.get("count", 0), kw])

    keywords = results.get("keywords") or {}
    if keywords.get("positive_keywords"):
        w.writerow([])
        w.writerow(["Positive Keyword", "Score"])
        for kw, score in keywords["positive_keywords"]:
            w.writerow([kw, round(float(score), 4)])
    if keywords.get("negative_keywords"):
        w.writerow([])
        w.writerow(["Negative Keyword", "Score"])
        for kw, score in keywords["negative_keywords"]:
            w.writerow([kw, round(float(score), 4)])

    insights = results.get("insights") or []
    if insights:
        w.writerow([])
        w.writerow(["Insight"])
        for i in insights:
            w.writerow([i])

    recs = results.get("recommendations") or []
    if recs:
        w.writerow([])
        w.writerow(["Recommendation"])
        for r in recs:
            w.writerow([r])

    summary_text = results.get("summary_text")
    if summary_text:
        w.writerow([])
        w.writerow(["Summary"])
        for line in summary_text.split("\n"):
            w.writerow([line])

    return buffer.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------

def export_results_pdf(results: Dict[str, Any], analysis_meta: Dict[str, Any]) -> bytes:
    """Render a clean PDF report. Returns the file as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="ReviewScope Report",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], spaceAfter=10, textColor=colors.HexColor("#1F2937"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#374151"))
    body = styles["BodyText"]
    body.spaceAfter = 4
    small = ParagraphStyle("Small", parent=body, fontSize=8, textColor=colors.HexColor("#6B7280"))

    story = []

    # ---- Header ----
    story.append(Paragraph("ReviewScope - Analysis Report", h1))
    story.append(Paragraph(
        f"File: {analysis_meta.get('file_name', '-')} | "
        f"Generated: {datetime.utcnow().isoformat(timespec='seconds')} UTC",
        small,
    ))
    story.append(Spacer(1, 8))

    # ---- What customers think (Conclusion goes FIRST in the PDF) ----
    summary_text = results.get("summary_text") or ""
    main_summary, conclusion_text = _split_conclusion(summary_text)
    if conclusion_text:
        story.append(Paragraph("What customers think", h2))
        for para in conclusion_text.split("\n\n"):
            for line in para.split("\n"):
                if line.strip():
                    story.append(Paragraph(_html_escape(line), body))
            story.append(Spacer(1, 4))

    # ---- Executive Summary (numbers at a glance) ----
    if main_summary:
        story.append(Paragraph("Executive Summary", h2))
        for para in main_summary.split("\n\n"):
            for line in para.split("\n"):
                if line.strip():
                    story.append(Paragraph(_html_escape(line), body))
            story.append(Spacer(1, 4))

    # ---- Sentiment ----
    sent = results.get("sentiment_summary") or {}
    if sent:
        story.append(Paragraph("Sentiment Distribution", h2))
        rows = [
            ["Total reviews", sent.get("total", "-")],
            ["Positive", f"{sent.get('positive', 0)} ({sent.get('positive_percent', 0):.1f}%)"],
            ["Negative", f"{sent.get('negative', 0)} ({sent.get('negative_percent', 0):.1f}%)"],
        ]
        story.append(_table(rows))

    # ---- Aspects ----
    aspects = (results.get("aspects") or {}).get("aspects") or []
    if aspects:
        story.append(Paragraph("Aspect-Based Sentiment Analysis", h2))
        rows = [["Aspect", "Mentions", "Positive%", "Negative%", "Polarity"]]
        for a in aspects[:15]:
            rows.append([
                a["aspect"],
                str(a["total_mentions"]),
                f"{a['positive_pct']:.0f}%",
                f"{a['negative_pct']:.0f}%",
                f"{a['polarity']:+.0f}",
            ])
        story.append(_table(rows, header=True))

    # ---- Topics ----
    topics = (results.get("topics") or {}).get("topics") or []
    if topics:
        story.append(Paragraph("Topic Modeling (BERTopic)", h2))
        rows = [["#", "Count", "Keywords"]]
        for idx, t in enumerate(topics[:10], start=1):
            rows.append([
                str(t.get("id", t.get("topic_id", idx))),
                str(t.get("count", 0)),
                ", ".join(t.get("keywords", [])[:6]),
            ])
        story.append(_table(rows, header=True))

    # ---- Keywords ----
    kw = results.get("keywords") or {}
    if kw.get("positive_keywords"):
        story.append(Paragraph("Top positive keywords", h2))
        story.append(Paragraph(
            ", ".join(f"{k} ({s:.2f})" for k, s in kw["positive_keywords"][:15]),
            body,
        ))
    if kw.get("negative_keywords"):
        story.append(Paragraph("Top negative keywords", h2))
        story.append(Paragraph(
            ", ".join(f"{k} ({s:.2f})" for k, s in kw["negative_keywords"][:15]),
            body,
        ))

    # ---- Insights ----
    if results.get("insights"):
        story.append(Paragraph("Insights", h2))
        for ins in results["insights"]:
            story.append(Paragraph(f"&#8226; {_html_escape(ins)}", body))

    # ---- Recommendations ----
    if results.get("recommendations"):
        story.append(Paragraph("Recommendations", h2))
        for rec in results["recommendations"]:
            story.append(Paragraph(f"&#8226; {_html_escape(rec)}", body))

    doc.build(story)
    return buffer.getvalue()


def _split_conclusion(summary_text: str) -> tuple[str, str]:
    """Split summary_text into (main, conclusion) at the CONCLUSION marker."""
    if not summary_text:
        return "", ""
    marker = "CONCLUSION"
    idx = summary_text.find(marker)
    if idx == -1:
        return summary_text, ""
    # Walk back to the start of the framing line of '=' chars above CONCLUSION.
    head = summary_text[:idx].rstrip()
    if head.endswith("="):
        last_nl = head.rfind("\n")
        if last_nl != -1:
            head = head[:last_nl].rstrip()
    # Walk forward past the trailing '=' line below CONCLUSION.
    rest = summary_text[idx + len(marker):]
    if rest.startswith("\n"):
        rest = rest[1:]
    if rest.startswith("="):
        nl = rest.find("\n")
        if nl != -1:
            rest = rest[nl + 1:]
    return head.strip(), rest.strip()


def _html_escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _table(rows: List[List[Any]], header: bool = False) -> Table:
    t = Table(rows, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    t.setStyle(TableStyle(style))
    return t
