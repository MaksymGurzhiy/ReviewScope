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
    quote = ParagraphStyle(
        "Quote", parent=body, leftIndent=12, fontSize=10,
        textColor=colors.HexColor("#374151"), spaceAfter=6,
    )

    story = []

    story.append(Paragraph("ReviewScope - Analysis Report", h1))
    story.append(Paragraph(
        f"File: {analysis_meta.get('file_name', '-')} | "
        f"Generated: {datetime.utcnow().isoformat(timespec='seconds')} UTC",
        small,
    ))
    story.append(Spacer(1, 8))

    # 01 - The brief: conclusion or top insights up front.
    summary_text = results.get("summary_text") or ""
    main_summary, conclusion_text = _split_conclusion(summary_text)
    insights = results.get("insights") or []
    if conclusion_text:
        story.append(Paragraph("The brief", h2))
        for para in conclusion_text.split("\n\n"):
            for line in para.split("\n"):
                if line.strip():
                    story.append(Paragraph(_html_escape(line), body))
            story.append(Spacer(1, 4))
    elif insights:
        story.append(Paragraph("The brief", h2))
        for ins in insights[:3]:
            story.append(Paragraph(f"&#8226; {_html_escape(ins)}", body))

    # 02/03 - Narrative aspect stories (worst / best).
    aspects_list = (results.get("aspects") or {}).get("aspects") or []
    wrong = _pick_aspect_stories(aspects_list, side="bad", n=4)
    good = _pick_aspect_stories(aspects_list, side="good", n=4)
    if wrong:
        story.append(Paragraph("What's not working", h2))
        for i, a in enumerate(wrong, start=1):
            phrases = ", ".join(a["phrases"]) if a["phrases"] else "-"
            story.append(Paragraph(
                f"<b>{i:02d}. {_html_escape(a['aspect'])}</b> &nbsp; "
                f"<font size=8 color='#6B7280'>{a['total']} mentions &middot; net &minus;{a['pct']}</font>",
                body,
            ))
            story.append(Paragraph(
                f"<font color='#7F1D1D'>Customers complain about: {_html_escape(phrases)}</font>",
                quote,
            ))
    if good:
        story.append(Paragraph("What's working", h2))
        for i, a in enumerate(good, start=1):
            phrases = ", ".join(a["phrases"]) if a["phrases"] else "-"
            story.append(Paragraph(
                f"<b>{i:02d}. {_html_escape(a['aspect'])}</b> &nbsp; "
                f"<font size=8 color='#6B7280'>{a['total']} mentions &middot; net +{a['pct']}</font>",
                body,
            ))
            story.append(Paragraph(
                f"<font color='#14532D'>Customers praise: {_html_escape(phrases)}</font>",
                quote,
            ))

    # 04 - Voices, in their own words.
    samples = results.get("sample_reviews") or []
    if samples:
        story.append(Paragraph("Voices, in their own words", h2))
        for i, r in enumerate(samples[:6], start=1):
            sent = str(r.get("sentiment") or "neutral").upper()
            color = {"POSITIVE": "#14532D", "NEGATIVE": "#7F1D1D"}.get(sent, "#78350F")
            text = (r.get("text") or "").strip()
            if len(text) > 360:
                text = text[:357].rstrip() + "..."
            rating = r.get("rating")
            rating_str = f" &middot; {rating}/5" if isinstance(rating, (int, float)) else ""
            story.append(Paragraph(
                f"<font size=8 color='{color}'>#{i:02d} &middot; {sent}{rating_str}</font>",
                small,
            ))
            story.append(Paragraph(f"&ldquo;{_html_escape(text)}&rdquo;", quote))

    # 05 - Recommendations (action items, surfaced before raw analytics).
    if results.get("recommendations"):
        story.append(Paragraph("What to do next", h2))
        for i, rec in enumerate(results["recommendations"], start=1):
            story.append(Paragraph(f"<b>{i:02d}.</b> {_html_escape(rec)}", body))

    # 06 - Full aspect table.
    if aspects_list:
        story.append(Paragraph("Top aspects, ranked", h2))
        rows = [["Aspect", "Mentions", "Positive%", "Negative%", "Polarity"]]
        for a in aspects_list[:15]:
            rows.append([
                a["aspect"],
                str(a["total_mentions"]),
                f"{a['positive_pct']:.0f}%",
                f"{a['negative_pct']:.0f}%",
                f"{a['polarity']:+.0f}",
            ])
        story.append(_table(rows, header=True))

    # 07 - Sentiment distribution.
    sent = results.get("sentiment_summary") or {}
    if sent:
        story.append(Paragraph("Sentiment distribution", h2))
        rows = [
            ["Total reviews", sent.get("total", "-")],
            ["Positive", f"{sent.get('positive', 0)} ({sent.get('positive_percent', 0):.1f}%)"],
            ["Neutral", f"{sent.get('neutral', 0)} ({sent.get('neutral_percent', 0):.1f}%)"],
            ["Negative", f"{sent.get('negative', 0)} ({sent.get('negative_percent', 0):.1f}%)"],
        ]
        story.append(_table(rows))

    # 08 - Keyword bands.
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

    # 09 - Topics.
    topics = (results.get("topics") or {}).get("topics") or []
    if topics:
        story.append(Paragraph("Themes the model surfaced", h2))
        rows = [["#", "Count", "Keywords"]]
        for idx, t in enumerate(topics[:10], start=1):
            rows.append([
                str(t.get("id", t.get("topic_id", idx))),
                str(t.get("count", 0)),
                ", ".join(t.get("keywords", [])[:6]),
            ])
        story.append(_table(rows, header=True))

    # 10 - Executive summary numbers (kept for completeness, last).
    if main_summary:
        story.append(Paragraph("Executive summary", h2))
        for para in main_summary.split("\n\n"):
            for line in para.split("\n"):
                if line.strip():
                    story.append(Paragraph(_html_escape(line), body))
            story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()


def _pick_aspect_stories(aspects: List[Dict[str, Any]], *, side: str, n: int = 4) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in aspects or []:
        total = a.get("total_mentions") or (a.get("positive", 0) + a.get("negative", 0) + a.get("neutral", 0)) or 1
        pos = a.get("positive", 0)
        neg = a.get("negative", 0)
        score = (pos - neg) / total
        praise = (
            a.get("praise_words")
            or a.get("opinions_positive")
            or a.get("context_positive")
            or a.get("positive_words")
            or []
        )[:3]
        complaints = (
            a.get("complaint_words")
            or a.get("opinions_negative")
            or a.get("context_negative")
            or a.get("negative_words")
            or []
        )[:3]
        if side == "good" and score > 0.05 and praise:
            out.append({"aspect": a["aspect"], "score": score, "total": total,
                        "phrases": list(praise), "pct": round(abs(score) * 100)})
        elif side == "bad" and score < -0.05 and complaints:
            out.append({"aspect": a["aspect"], "score": score, "total": total,
                        "phrases": list(complaints), "pct": round(abs(score) * 100)})
    out.sort(key=lambda x: (-x["score"] if side == "good" else x["score"], -x["total"]))
    return out[:n]


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
