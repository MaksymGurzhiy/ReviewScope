"""Project CRUD routes."""
from typing import List

from fastapi import APIRouter, HTTPException, status

from src.api.auth import CurrentUserDep, CurrentUser
from src.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from src.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectOut])
def list_projects(user: CurrentUser = CurrentUserDep):
    return project_service.list_projects(user.id)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: CurrentUser = CurrentUserDep):
    return project_service.create_project(user.id, payload)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: CurrentUser = CurrentUserDep):
    project = project_service.get_project(user.id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user: CurrentUser = CurrentUserDep,
):
    project = project_service.update_project(user.id, project_id, payload)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: CurrentUser = CurrentUserDep):
    if not project_service.delete_project(user.id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return None
