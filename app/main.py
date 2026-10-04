import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import (
    init_db,
    get_all_projects,
    get_project_by_id,
    create_project,
    update_project,
    delete_project,
    duplicate_project,
    get_stats
)
from .scanner import scan_directory_for_projects, sync_project_from_disk

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="ProjectHub - Fichas de Proyectos",
    description="Aplicación local para gestionar fichas técnicas y funcionales de proyectos e ideas",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Models
class StepItem(BaseModel):
    text: str
    done: bool = False

class ProjectCreate(BaseModel):
    title: str
    summary: Optional[str] = ""
    status: Optional[str] = "idea"
    category: Optional[str] = "Otro"
    priority: Optional[str] = "media"
    tags: Optional[List[str]] = []
    functional_scope: Optional[str] = ""
    technical_stack: Optional[str] = ""
    local_path: Optional[str] = ""
    repo_url: Optional[str] = ""
    run_command: Optional[str] = ""
    technical_notes: Optional[str] = ""
    next_steps: Optional[List[StepItem]] = []
    notes: Optional[str] = ""

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    functional_scope: Optional[str] = None
    technical_stack: Optional[str] = None
    local_path: Optional[str] = None
    repo_url: Optional[str] = None
    run_command: Optional[str] = None
    technical_notes: Optional[str] = None
    next_steps: Optional[List[StepItem]] = None
    notes: Optional[str] = None

class ToggleStepRequest(BaseModel):
    step_index: int
    done: bool

# API Endpoints
@app.get("/api/stats")
def api_get_stats():
    return get_stats()

@app.get("/api/projects")
def api_get_projects(
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: Optional[str] = "updated_at"
):
    projects = get_all_projects(
        search=search,
        status=status,
        category=category,
        tag=tag,
        sort_by=sort_by
    )
    return projects

@app.get("/api/projects/{project_id}")
def api_get_project(project_id: int):
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project

@app.post("/api/projects")
def api_create_project(project_data: ProjectCreate):
    data_dict = project_data.dict()
    new_project = create_project(data_dict)
    return new_project

@app.put("/api/projects/{project_id}")
def api_update_project(project_id: int, project_data: ProjectUpdate):
    data_dict = {k: v for k, v in project_data.dict().items() if v is not None}
    updated = update_project(project_id, data_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return updated

@app.delete("/api/projects/{project_id}")
def api_delete_project(project_id: int):
    success = delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"success": True, "message": "Proyecto eliminado"}

@app.post("/api/projects/{project_id}/duplicate")
def api_duplicate_project(project_id: int):
    duplicated = duplicate_project(project_id)
    if not duplicated:
        raise HTTPException(status_code=404, detail="No se pudo duplicar")
    return duplicated

@app.post("/api/projects/{project_id}/sync-disk")
def api_sync_project(project_id: int):
    updated, changes = sync_project_from_disk(project_id)
    if updated is None:
        raise HTTPException(status_code=400, detail=changes)
    return {"project": updated, "changes": changes}

@app.post("/api/projects/{project_id}/toggle-step")
def api_toggle_step(project_id: int, req: ToggleStepRequest):
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    steps = project.get("next_steps", [])
    if 0 <= req.step_index < len(steps):
        steps[req.step_index]["done"] = req.done
        update_project(project_id, {"next_steps": steps})
        return {"success": True, "next_steps": steps}
    raise HTTPException(status_code=400, detail="Índice de paso inválido")

@app.get("/api/scan")
def api_scan_directory(path: Optional[str] = "/home/ubuntu"):
    candidates = scan_directory_for_projects(path)
    return {"base_path": path, "candidates": candidates}

@app.post("/api/import-scanned")
def api_import_scanned(projects: List[ProjectCreate]):
    imported = []
    for p in projects:
        data = p.dict()
        new_p = create_project(data)
        imported.append(new_p)
    return {"imported_count": len(imported), "projects": imported}

@app.get("/api/export")
def api_export_backup():
    projects = get_all_projects()
    return JSONResponse(
        content={"backup_version": "1.0", "projects": projects},
        headers={"Content-Disposition": "attachment; filename=proyectos_backup.json"}
    )

@app.post("/api/import")
def api_import_backup(data: Dict[str, Any]):
    projects_list = data.get("projects", [])
    imported_count = 0
    for p in projects_list:
        p_data = {
            "title": p.get("title", "Sin título"),
            "summary": p.get("summary", ""),
            "status": p.get("status", "idea"),
            "category": p.get("category", "Otro"),
            "priority": p.get("priority", "media"),
            "tags": p.get("tags", []),
            "functional_scope": p.get("functional_scope", ""),
            "technical_stack": p.get("technical_stack", ""),
            "local_path": p.get("local_path", ""),
            "repo_url": p.get("repo_url", ""),
            "run_command": p.get("run_command", ""),
            "technical_notes": p.get("technical_notes", ""),
            "next_steps": p.get("next_steps", []),
            "notes": p.get("notes", "")
        }
        create_project(p_data)
        imported_count += 1
    return {"success": True, "imported_count": imported_count}

# Frontend Serving
INDEX_HTML_PATH = BASE_DIR / "templates" / "index.html"

@app.get("/", response_class=HTMLResponse)
def serve_index():
    if not INDEX_HTML_PATH.exists():
        return HTMLResponse("<h1>ProjectHub cargando...</h1>")
    return HTMLResponse(INDEX_HTML_PATH.read_text(encoding="utf-8"))
