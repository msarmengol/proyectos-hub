import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "projects.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        summary TEXT,
        status TEXT NOT NULL DEFAULT 'idea',
        category TEXT DEFAULT 'Otro',
        priority TEXT DEFAULT 'media',
        tags TEXT DEFAULT '[]',
        functional_scope TEXT,
        technical_stack TEXT,
        local_path TEXT,
        repo_url TEXT,
        run_command TEXT,
        technical_notes TEXT,
        next_steps TEXT DEFAULT '[]',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

def row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    # Parse tags if JSON
    if d.get("tags"):
        try:
            d["tags"] = json.loads(d["tags"])
        except Exception:
            d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]
    else:
        d["tags"] = []

    # Parse next_steps if JSON
    if d.get("next_steps"):
        try:
            d["next_steps"] = json.loads(d["next_steps"])
        except Exception:
            # Fallback to plain lines converted to steps
            lines = [l.strip() for l in d["next_steps"].split("\n") if l.strip()]
            d["next_steps"] = [{"text": l, "done": False} for l in lines]
    else:
        d["next_steps"] = []

    return d

def get_all_projects(search: str = None, status: str = None, category: str = None, tag: str = None, sort_by: str = "updated_at"):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM projects WHERE 1=1"
    params = []
    
    if status and status.lower() != "todos":
        query += " AND status = ?"
        params.append(status.lower())
        
    if category and category.lower() != "todas":
        query += " AND category = ?"
        params.append(category)
        
    if search:
        search_param = f"%{search.lower()}%"
        query += """ AND (
            LOWER(title) LIKE ? OR 
            LOWER(summary) LIKE ? OR 
            LOWER(functional_scope) LIKE ? OR 
            LOWER(technical_stack) LIKE ? OR 
            LOWER(tags) LIKE ? OR
            LOWER(local_path) LIKE ?
        )"""
        params.extend([search_param] * 6)
        
    if tag:
        tag_param = f"%{tag.lower()}%"
        query += " AND LOWER(tags) LIKE ?"
        params.append(tag_param)
        
    if sort_by == "title":
        query += " ORDER BY title COLLATE NOCASE ASC"
    elif sort_by == "priority":
        query += " ORDER BY CASE priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 WHEN 'baja' THEN 3 ELSE 4 END ASC, updated_at DESC"
    elif sort_by == "created_at":
        query += " ORDER BY created_at DESC"
    else:
        query += " ORDER BY updated_at DESC"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def get_project_by_id(project_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return row_to_dict(row)

def create_project(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    tags = data.get("tags", [])
    if isinstance(tags, list):
        tags_str = json.dumps(tags)
    else:
        tags_str = json.dumps([t.strip() for t in str(tags).split(",") if t.strip()])
        
    next_steps = data.get("next_steps", [])
    if isinstance(next_steps, list):
        steps_str = json.dumps(next_steps)
    else:
        steps_str = json.dumps([{"text": s.strip(), "done": False} for s in str(next_steps).split("\n") if s.strip()])
        
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO projects (
        title, summary, status, category, priority, tags,
        functional_scope, technical_stack, local_path, repo_url,
        run_command, technical_notes, next_steps, notes,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title", "Sin título").strip(),
        data.get("summary", ""),
        data.get("status", "idea").lower(),
        data.get("category", "Otro"),
        data.get("priority", "media").lower(),
        tags_str,
        data.get("functional_scope", ""),
        data.get("technical_stack", ""),
        data.get("local_path", ""),
        data.get("repo_url", ""),
        data.get("run_command", ""),
        data.get("technical_notes", ""),
        steps_str,
        data.get("notes", ""),
        now,
        now
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_project_by_id(new_id)

def update_project(project_id: int, data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    tags = data.get("tags")
    if tags is not None:
        if isinstance(tags, list):
            tags_str = json.dumps(tags)
        else:
            tags_str = json.dumps([t.strip() for t in str(tags).split(",") if t.strip()])
    else:
        tags_str = None
        
    next_steps = data.get("next_steps")
    if next_steps is not None:
        if isinstance(next_steps, list):
            steps_str = json.dumps(next_steps)
        else:
            steps_str = json.dumps([{"text": s.strip(), "done": False} for s in str(next_steps).split("\n") if s.strip()])
    else:
        steps_str = None
        
    now = datetime.now().isoformat()
    
    fields = []
    params = []
    
    updatable = [
        ("title", data.get("title")),
        ("summary", data.get("summary")),
        ("status", data.get("status").lower() if data.get("status") else None),
        ("category", data.get("category")),
        ("priority", data.get("priority").lower() if data.get("priority") else None),
        ("tags", tags_str),
        ("functional_scope", data.get("functional_scope")),
        ("technical_stack", data.get("technical_stack")),
        ("local_path", data.get("local_path")),
        ("repo_url", data.get("repo_url")),
        ("run_command", data.get("run_command")),
        ("technical_notes", data.get("technical_notes")),
        ("next_steps", steps_str),
        ("notes", data.get("notes")),
    ]
    
    for field_name, value in updatable:
        if value is not None:
            fields.append(f"{field_name} = ?")
            params.append(value)
            
    fields.append("updated_at = ?")
    params.append(now)
    params.append(project_id)
    
    query = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return get_project_by_id(project_id)

def delete_project(project_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def duplicate_project(project_id: int):
    orig = get_project_by_id(project_id)
    if not orig:
        return None
    data = orig.copy()
    data.pop("id", None)
    data["title"] = f"{orig['title']} (Copia)"
    data["status"] = "idea"
    return create_project(data)

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM projects")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT status, COUNT(*) FROM projects GROUP BY status")
    status_counts = dict(cursor.fetchall())
    
    cursor.execute("SELECT category, COUNT(*) FROM projects GROUP BY category")
    category_counts = dict(cursor.fetchall())
    
    conn.close()
    return {
        "total": total,
        "idea": status_counts.get("idea", 0),
        "desarrollo": status_counts.get("desarrollo", 0),
        "produccion": status_counts.get("produccion", 0),
        "pausado": status_counts.get("pausado", 0),
        "archivado": status_counts.get("archivado", 0),
        "categories": category_counts
    }
