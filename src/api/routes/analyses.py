"""Analysis routes: upload + run + history."""
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.api.auth import CurrentUser, CurrentUserDep
from src.schemas.analysis import AnalysisOut, AnalysisRequest, AnalysisResponse
from src.services import analysis_service, project_service, storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analyses", tags=["analyses"])

_executor = ThreadPoolExecutor(max_workers=2)

_ALLOWED_FORMATS = {".csv": "csv", ".xlsx": "xlsx", ".xls": "xls", ".json": "json"}


@router.get("", response_model=List[AnalysisOut])
def list_analyses(
    project_id: Optional[str] = None,
    user: CurrentUser = CurrentUserDep,
):
    return analysis_service.list_analyses(user.id, project_id=project_id)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, user: CurrentUser = CurrentUserDep):
    a = analysis_service.get_analysis(user.id, analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    result = analysis_service.get_result(analysis_id)
    return AnalysisResponse(analysis=a, result=result)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: str, user: CurrentUser = CurrentUserDep):
    a = analysis_service.get_analysis(user.id, analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if a.file_path:
        storage_service.delete_review_file(a.file_path)
    analysis_service.delete_analysis(user.id, analysis_id)
    return None


# ---------------------------------------------------------------------
# Upload + run
# ---------------------------------------------------------------------

@router.post("/upload", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
async def upload_and_register(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = CurrentUserDep,
):
    """Upload a file and create an analysis record (status='pending')."""
    # validate project ownership
    project = project_service.get_project(user.id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix}. Allowed: {list(_ALLOWED_FORMATS)}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    # 1. create row to obtain analysis_id
    analysis = analysis_service.create_analysis(
        user_id=user.id,
        project_id=project_id,
        file_name=file.filename,
        file_path="",
        file_size=len(file_bytes),
        file_format=_ALLOWED_FORMATS[suffix],
    )

    # 2. upload bytes to storage under <user_id>/<analysis_id>/<filename>
    storage_path = storage_service.upload_review_file(
        user_id=user.id,
        analysis_id=analysis.id,
        filename=file.filename,
        file_bytes=file_bytes,
    )

    # 3. patch the row with the storage path
    analysis_service.set_file_path(analysis.id, storage_path)
    analysis.file_path = storage_path
    return analysis


def _run_pipeline_safely(analysis_id: str, local: Path, payload: AnalysisRequest) -> None:
    """Worker invoked by the thread pool: runs the pipeline, then deletes the temp file."""
    try:
        analysis_service.run_and_store(
            analysis_id=analysis_id,
            local_file_path=local,
            options=payload,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Pipeline failed for analysis %s", analysis_id)
    finally:
        try:
            local.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass


@router.post("/{analysis_id}/run", response_model=AnalysisOut, status_code=status.HTTP_202_ACCEPTED)
async def run_analysis(
    analysis_id: str,
    payload: AnalysisRequest,
    user: CurrentUser = CurrentUserDep,
):
    """Trigger pipeline execution for an existing analysis row (fire-and-forget)."""
    a = analysis_service.get_analysis(user.id, analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if not a.file_path:
        raise HTTPException(status_code=400, detail="Analysis has no associated file.")

    local = storage_service.download_to_tempfile(a.file_path)
    analysis_service.update_analysis_status(
        analysis_id,
        "processing",
        progress_stage="queued",
        progress_pct=1,
        error_message="",
    )
    _executor.submit(_run_pipeline_safely, analysis_id, local, payload)

    return analysis_service.get_analysis(user.id, analysis_id) or a
