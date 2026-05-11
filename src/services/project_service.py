"""CRUD operations for projects (uses Supabase via service-role client)."""
from typing import List, Optional

from src.database.supabase_client import get_supabase_admin
from src.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate


def _to_out(row: dict, analyses_count: int = 0) -> ProjectOut:
    return ProjectOut(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        description=row.get("description"),
        language=row.get("language"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        analyses_count=analyses_count,
    )


def list_projects(user_id: str) -> List[ProjectOut]:
    sb = get_supabase_admin()

    projects = (
        sb.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    if not projects:
        return []

    project_ids = [p["id"] for p in projects]
    counts_data = (
        sb.table("analyses")
        .select("project_id")
        .in_("project_id", project_ids)
        .execute()
        .data
        or []
    )
    counts: dict[str, int] = {}
    for row in counts_data:
        counts[row["project_id"]] = counts.get(row["project_id"], 0) + 1

    return [_to_out(p, counts.get(p["id"], 0)) for p in projects]


def get_project(user_id: str, project_id: str) -> Optional[ProjectOut]:
    sb = get_supabase_admin()
    rows = (
        sb.table("projects")
        .select("*")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    count = (
        sb.table("analyses")
        .select("id", count="exact")
        .eq("project_id", project_id)
        .execute()
    ).count or 0
    return _to_out(rows[0], count)


def create_project(user_id: str, data: ProjectCreate) -> ProjectOut:
    sb = get_supabase_admin()
    payload = data.model_dump(exclude_none=True)
    payload["user_id"] = user_id
    row = sb.table("projects").insert(payload).execute().data[0]
    return _to_out(row, 0)


def update_project(user_id: str, project_id: str, data: ProjectUpdate) -> Optional[ProjectOut]:
    sb = get_supabase_admin()
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_project(user_id, project_id)

    rows = (
        sb.table("projects")
        .update(payload)
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
        .data
    )
    if not rows:
        return None
    return _to_out(rows[0], 0)


def delete_project(user_id: str, project_id: str) -> bool:
    sb = get_supabase_admin()
    rows = (
        sb.table("projects")
        .delete()
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
        .data
    )
    return bool(rows)
