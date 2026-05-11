"""
Analysis lifecycle: create -> run pipeline -> store results.

This module orchestrates:
    - inserting an `analyses` row (status='processing')
    - running the NLP pipeline (sentiment, ABSA, topics, keywords, summary)
    - inserting a `results` row
    - marking the analysis as 'completed' / 'failed'
"""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

import httpx

from src.database.supabase_client import get_supabase_admin, reset_supabase_admin
from src.parsers.parser_factory import ParserFactory
from src.schemas.analysis import AnalysisOut, AnalysisRequest, ResultOut

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Transient httpx errors that mean "the connection died, recreate and retry".
_TRANSIENT_EXC = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectError,
    httpx.PoolTimeout,
)


def _with_retry(fn: Callable[[], T], *, attempts: int = 3, op: str = "supabase") -> T:
    """Run a Supabase call with retry-on-transient-error semantics.

    On the first transient error we drop the cached admin client and rebuild
    it for the next attempt; this protects against stale HTTP keep-alive
    sockets that Supabase has already closed on its side.
    """
    last_exc: Optional[Exception] = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except _TRANSIENT_EXC as exc:
            last_exc = exc
            logger.warning(
                "%s attempt %d/%d failed (%s: %s); resetting client",
                op, i, attempts, type(exc).__name__, exc,
            )
            reset_supabase_admin()
            time.sleep(0.4 * i)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------

def _analysis_to_out(row: dict) -> AnalysisOut:
    return AnalysisOut(
        id=row["id"],
        project_id=row["project_id"],
        user_id=row["user_id"],
        file_name=row["file_name"],
        file_path=row.get("file_path"),
        file_size=row.get("file_size"),
        file_format=row.get("file_format"),
        total_reviews=row.get("total_reviews", 0),
        status=row["status"],
        error_message=row.get("error_message"),
        progress_stage=row.get("progress_stage"),
        progress_pct=row.get("progress_pct") or 0,
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
        duration_ms=row.get("duration_ms"),
    )


def _result_to_out(row: dict) -> ResultOut:
    return ResultOut(
        id=row["id"],
        analysis_id=row["analysis_id"],
        sentiment_summary=row.get("sentiment_summary"),
        aspects=row.get("aspects"),
        topics=row.get("topics"),
        keywords=row.get("keywords"),
        summary_text=row.get("summary_text"),
        insights=row.get("insights"),
        recommendations=row.get("recommendations"),
        metrics=row.get("metrics"),
        sample_reviews=row.get("sample_reviews"),
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------
# CRUD - analyses
# ---------------------------------------------------------------------

def create_analysis(
    *,
    user_id: str,
    project_id: str,
    file_name: str,
    file_path: str,
    file_size: int,
    file_format: str,
) -> AnalysisOut:
    payload = {
        "user_id": user_id,
        "project_id": project_id,
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "file_format": file_format,
        "status": "pending",
    }

    def _do():
        sb = get_supabase_admin()
        return sb.table("analyses").insert(payload).execute().data[0]

    row = _with_retry(_do, op="create_analysis")
    return _analysis_to_out(row)


def set_file_path(analysis_id: str, file_path: str) -> None:
    def _do():
        sb = get_supabase_admin()
        sb.table("analyses").update({"file_path": file_path}).eq("id", analysis_id).execute()

    _with_retry(_do, op="set_file_path")


def update_analysis_status(
    analysis_id: str,
    status: str,
    *,
    total_reviews: Optional[int] = None,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    progress_stage: Optional[str] = None,
    progress_pct: Optional[int] = None,
) -> None:
    patch: Dict[str, Any] = {"status": status}
    if total_reviews is not None:
        patch["total_reviews"] = total_reviews
    if error_message is not None:
        patch["error_message"] = error_message
    if duration_ms is not None:
        patch["duration_ms"] = duration_ms
    if progress_stage is not None:
        patch["progress_stage"] = progress_stage
    if progress_pct is not None:
        patch["progress_pct"] = max(0, min(100, int(progress_pct)))
    if status in ("completed", "failed"):
        patch["completed_at"] = datetime.now(timezone.utc).isoformat()

    def _do():
        sb = get_supabase_admin()
        sb.table("analyses").update(patch).eq("id", analysis_id).execute()

    _with_retry(_do, op=f"update_analysis_status({status})")


def update_progress(analysis_id: str, stage: str, pct: int) -> None:
    """Lightweight progress update during pipeline execution."""
    patch = {
        "progress_stage": stage,
        "progress_pct": max(0, min(100, int(pct))),
    }

    def _do():
        sb = get_supabase_admin()
        sb.table("analyses").update(patch).eq("id", analysis_id).execute()

    _with_retry(_do, op=f"update_progress({stage})")


def get_analysis(user_id: str, analysis_id: str) -> Optional[AnalysisOut]:
    def _do():
        sb = get_supabase_admin()
        return (
            sb.table("analyses")
            .select("*")
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )

    rows = _with_retry(_do, op="get_analysis")
    return _analysis_to_out(rows[0]) if rows else None


def list_analyses(user_id: str, project_id: Optional[str] = None) -> List[AnalysisOut]:
    def _do():
        sb = get_supabase_admin()
        q = sb.table("analyses").select("*").eq("user_id", user_id)
        if project_id:
            q = q.eq("project_id", project_id)
        return q.order("created_at", desc=True).execute().data or []

    rows = _with_retry(_do, op="list_analyses")
    return [_analysis_to_out(r) for r in rows]


def delete_analysis(user_id: str, analysis_id: str) -> bool:
    def _do():
        sb = get_supabase_admin()
        return (
            sb.table("analyses")
            .delete()
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .execute()
            .data
        )

    rows = _with_retry(_do, op="delete_analysis")
    return bool(rows)


# ---------------------------------------------------------------------
# CRUD - results
# ---------------------------------------------------------------------

def upsert_result(analysis_id: str, payload: Dict[str, Any]) -> ResultOut:
    payload = {**payload, "analysis_id": analysis_id}

    def _do():
        sb = get_supabase_admin()
        return (
            sb.table("results")
            .upsert(payload, on_conflict="analysis_id")
            .execute()
            .data
        )

    rows = _with_retry(_do, op="upsert_result")
    return _result_to_out(rows[0])


def get_result(analysis_id: str) -> Optional[ResultOut]:
    def _do():
        sb = get_supabase_admin()
        return (
            sb.table("results")
            .select("*")
            .eq("analysis_id", analysis_id)
            .limit(1)
            .execute()
            .data
            or []
        )

    rows = _with_retry(_do, op="get_result")
    return _result_to_out(rows[0]) if rows else None


# ---------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------

def run_pipeline(
    local_file_path: Path,
    options: AnalysisRequest,
    sample_limit: int = 20,
    on_progress=None,
    display_file_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full NLP pipeline on a local file and return a result payload
    suitable for the `results` table.

    `display_file_name` is the original name uploaded by the user (used for
    the per-dataset NLP blocklist). `local_file_path.name` is a random tmp
    name and is unsuitable for that purpose.

    Heavy ML imports happen lazily so the API process stays light.
    """
    from src.nlp.pipeline import NLPPipeline, _noop   # local import to defer model load

    cb = on_progress or _noop
    cb("parsing", 2)
    reviews = ParserFactory.parse_file(local_file_path)
    if not reviews:
        raise ValueError("Parser returned 0 reviews from the uploaded file.")

    pipeline = NLPPipeline()
    payload = pipeline.run(
        reviews,
        options=options,
        on_progress=cb,
        file_name=display_file_name or local_file_path.name,
    )

    # trim sample reviews to keep DB row small
    if "sample_reviews" in payload and isinstance(payload["sample_reviews"], list):
        payload["sample_reviews"] = payload["sample_reviews"][:sample_limit]

    return payload


def run_and_store(
    *,
    analysis_id: str,
    local_file_path: Path,
    options: AnalysisRequest,
) -> ResultOut:
    """Run the pipeline and persist results. Updates `analyses.status` accordingly."""
    # Look up the original file name (the storage tmp file has a random name
    # which we don't want feeding into the NLP blocklist).
    display_file_name: Optional[str] = None
    try:
        sb = get_supabase_admin()
        rows = (
            sb.table("analyses").select("file_name")
            .eq("id", analysis_id).limit(1).execute().data or []
        )
        if rows:
            display_file_name = rows[0].get("file_name")
    except Exception:  # noqa: BLE001
        logger.debug("Could not fetch display_file_name from DB", exc_info=True)

    logger.info("=" * 70)
    logger.info(
        "Pipeline START | analysis_id=%s | tmp=%s | display=%s",
        analysis_id, local_file_path.name, display_file_name,
    )
    logger.info("=" * 70)
    started = time.perf_counter()
    update_analysis_status(analysis_id, "processing", progress_stage="starting", progress_pct=1)

    def _progress(stage: str, pct: int) -> None:
        try:
            update_progress(analysis_id, stage, pct)
        except Exception:  # noqa: BLE001
            logger.debug("progress update failed", exc_info=True)

    try:
        payload = run_pipeline(
            local_file_path,
            options=options,
            on_progress=_progress,
            display_file_name=display_file_name,
        )
        _progress("saving", 98)
        total = payload.get("metrics", {}).get("total_reviews") or len(payload.get("sample_reviews", []))
        result = upsert_result(analysis_id, payload)
        duration_ms = int((time.perf_counter() - started) * 1000)
        update_analysis_status(
            analysis_id,
            "completed",
            total_reviews=total or 0,
            duration_ms=duration_ms,
            progress_stage="completed",
            progress_pct=100,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("Pipeline failed for analysis %s", analysis_id)
        try:
            update_analysis_status(
                analysis_id,
                "failed",
                error_message=str(exc)[:500],
                duration_ms=duration_ms,
                progress_stage="failed",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to mark analysis %s as failed", analysis_id)
        raise
