"""Export results as PDF or CSV."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.api.auth import CurrentUser, CurrentUserDep
from src.services import analysis_service, export_service

router = APIRouter(prefix="/api/analyses/{analysis_id}/export", tags=["exports"])


def _load(user_id: str, analysis_id: str):
    a = analysis_service.get_analysis(user_id, analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if a.status != "completed":
        raise HTTPException(status_code=400, detail="Analysis is not completed yet.")
    result = analysis_service.get_result(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="No results to export.")
    return a, result


@router.get("/csv")
def export_csv(analysis_id: str, user: CurrentUser = CurrentUserDep):
    a, result = _load(user.id, analysis_id)
    payload = result.model_dump()
    blob = export_service.export_results_csv(payload)
    return Response(
        content=blob,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="reviewscope_{analysis_id}.csv"'},
    )


@router.get("/pdf")
def export_pdf(analysis_id: str, user: CurrentUser = CurrentUserDep):
    a, result = _load(user.id, analysis_id)
    payload = result.model_dump()
    blob = export_service.export_results_pdf(payload, a.model_dump())
    return Response(
        content=blob,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reviewscope_{analysis_id}.pdf"'},
    )
