"""Current user / profile routes."""
from fastapi import APIRouter, HTTPException

from src.api.auth import CurrentUser, CurrentUserDep
from src.database.supabase_client import get_supabase_admin

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("")
def me(user: CurrentUser = CurrentUserDep):
    sb = get_supabase_admin()
    rows = (
        sb.table("profiles")
        .select("id, email, full_name, avatar_url, plan, api_key, created_at, updated_at")
        .eq("id", user.id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        # Profile row may be missing the very first time (race with the trigger)
        return {"id": user.id, "email": user.email}
    return rows[0]


@router.post("/api-key/rotate")
def rotate_api_key(user: CurrentUser = CurrentUserDep):
    """Generate a fresh personal API key (replaces the old one)."""
    import secrets
    new_key = secrets.token_hex(32)
    sb = get_supabase_admin()
    sb.table("profiles").update({"api_key": new_key}).eq("id", user.id).execute()
    return {"api_key": new_key}
