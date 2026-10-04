import os
import re
import json
from pathlib import Path
from .database import get_all_projects, get_project_by_id, update_project

IGNORE_DIRS = {
    ".git", ".cache", ".config", ".local", ".npm", ".vscode-server",
    ".gemini", ".hermes", ".copilot", ".agent-browser", ".aider",
    ".cua-driver", "snap", "__pycache__", "node_modules", "venv", ".venv"
}

def extract_git_remote(dir_path: Path):
    git_config = dir_path / ".git" / "config"
    if not git_config.exists():
        return ""
    try:
        content = git_config.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r'url\s*=\s*(https?://[^\s]+|git@[^\s]+)', content)
        if match:
            url = match.group(1).strip()
            # Convert git@github.com:user/repo.git to https://github.com/user/repo
            if url.startswith("git@github.com:"):
                url = "https://github.com/" + url[len("git@github.com:"):].removesuffix(".git")
            return url
    except Exception:
        pass
    return ""

def parse_readme(readme_path: Path):
    title = ""
    summary = ""
    scope = ""
    try:
        content = readme_path.read_text(encoding="utf-8", errors="ignore")
        lines = [line.strip() for line in content.split("\n")]
        
        # Look for first # Header
        for line in lines:
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                break
                
        # Look for description / summary
        paragraphs = []
        curr = []
        for line in lines:
            if line.startswith("#"):
                if curr:
                    paragraphs.append("\n".join(curr).strip())
                    curr = []
            elif line:
                curr.append(line)
            else:
                if curr:
                    paragraphs.append("\n".join(curr).strip())
                    curr = []
        if curr:
            paragraphs.append("\n".join(curr).strip())
            
        if paragraphs:
            summary = paragraphs[0][:250] + ("..." if len(paragraphs[0]) > 250 else "")
            scope = "\n\n".join(paragraphs[:3])
    except Exception:
        pass
    return title, summary, scope

def detect_project_details(dir_path: Path):
    name = dir_path.name
    tags = []
    stack_items = []
    category = "Otro"
    run_cmd = ""
    title = name.replace("-", " ").replace("_", " ").title()
    summary = f"Proyecto detectado en {dir_path}"
    scope = ""
    
    # 1. Readme
    for rname in ["README.md", "readme.md", "README.txt", "README"]:
        rpath = dir_path / rname
        if rpath.exists():
            rtitle, rsum, rscope = parse_readme(rpath)
            if rtitle:
                title = rtitle
            if rsum:
                summary = rsum
            if rscope:
                scope = rscope
            break

    # 2. Python check
    py_files = list(dir_path.glob("*.py"))
    has_reqs = (dir_path / "requirements.txt").exists() or (dir_path / "pyproject.toml").exists()
    if py_files or has_reqs:
        stack_items.append("Python")
        tags.append("python")
        category = "Backend"
        
        # Check requirements or code for frameworks
        req_content = ""
        if (dir_path / "requirements.txt").exists():
            try:
                req_content = (dir_path / "requirements.txt").read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                pass
                
        # Scan python imports
        sample_code = ""
        for py in py_files[:5]:
            try:
                sample_code += py.read_text(encoding="utf-8", errors="ignore").lower() + "\n"
            except Exception:
                pass
                
        all_py_text = req_content + " " + sample_code
        if "fastapi" in all_py_text:
            stack_items.append("FastAPI")
            tags.append("fastapi")
            run_cmd = "uvicorn main:app --reload"
        elif "flask" in all_py_text:
            stack_items.append("Flask")
            tags.append("flask")
            run_cmd = "python app.py"
        elif "django" in all_py_text:
            stack_items.append("Django")
            tags.append("django")
            run_cmd = "python manage.py runserver"
            
        if "openai" in all_py_text or "agent" in all_py_text or "langchain" in all_py_text or "anthropic" in all_py_text:
            category = "IA / Agentes"
            tags.append("ia")
            tags.append("agentes")

        if "sqlite" in all_py_text or any(dir_path.glob("*.db")) or any(dir_path.glob("*.sqlite")):
            stack_items.append("SQLite")
            tags.append("sqlite")

    # 3. Node/JS check
    pkg_json_path = dir_path / "package.json"
    if pkg_json_path.exists():
        tags.append("javascript")
        try:
            pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8", errors="ignore"))
            if not title or title == name.replace("-", " ").title():
                title = pkg_data.get("name", title)
            if not summary or "detectado en" in summary:
                summary = pkg_data.get("description", summary)
                
            deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            if "next" in deps:
                stack_items.extend(["Node.js", "Next.js", "React"])
                category = "Web"
                run_cmd = "npm run dev"
            elif "react" in deps:
                stack_items.extend(["Node.js", "React"])
                category = "Web"
                run_cmd = "npm run dev"
            elif "vue" in deps:
                stack_items.extend(["Node.js", "Vue"])
                category = "Web"
                run_cmd = "npm run dev"
            elif "express" in deps:
                stack_items.extend(["Node.js", "Express"])
                category = "Backend"
                run_cmd = "npm start"
            else:
                stack_items.append("Node.js")
        except Exception:
            stack_items.append("Node.js")

    # 4. Docker check
    if (dir_path / "docker-compose.yml").exists() or (dir_path / "compose.yaml").exists():
        stack_items.append("Docker Compose")
        tags.append("docker")
        if not run_cmd:
            run_cmd = "docker compose up -d"
        if "n8n" in name.lower():
            category = "Automatización"
    elif (dir_path / "Dockerfile").exists():
        stack_items.append("Docker")
        tags.append("docker")

    # Deduplicate stack items
    seen = set()
    cleaned_stack = []
    for item in stack_items:
        if item.lower() not in seen:
            seen.add(item.lower())
            cleaned_stack.append(item)
            
    repo_url = extract_git_remote(dir_path)
    
    return {
        "title": title,
        "summary": summary,
        "status": "desarrollo",
        "category": category,
        "priority": "media",
        "tags": list(set(tags)),
        "functional_scope": scope or f"Alcance funcional del proyecto {title}.",
        "technical_stack": ", ".join(cleaned_stack) if cleaned_stack else "Por definir",
        "local_path": str(dir_path.resolve()),
        "repo_url": repo_url,
        "run_command": run_cmd,
        "technical_notes": f"Detectado en {dir_path.resolve()}",
        "next_steps": [{"text": "Revisar y completar ficha", "done": False}],
        "notes": ""
    }

def scan_directory_for_projects(base_path: str = "/home/ubuntu"):
    root = Path(base_path).resolve()
    if not root.exists() or not root.is_dir():
        return []
        
    existing_projects = get_all_projects()
    saved_paths = {p.get("local_path", "").rstrip("/") for p in existing_projects if p.get("local_path")}
    
    # Check if root itself is a project (and not a system home directory)
    has_git = (root / ".git").is_dir()
    has_py = any(root.glob("*.py"))
    has_pkg = (root / "package.json").exists()
    has_docker = (root / "docker-compose.yml").exists() or (root / "Dockerfile").exists()
    has_readme = (root / "README.md").exists()
    
    if (has_git or has_py or has_pkg or has_docker or has_readme) and root.name not in ["ubuntu", "home", "root"]:
        detected = detect_project_details(root)
        detected["is_already_saved"] = str(root).rstrip("/") in saved_paths
        return [detected]
        
    candidates = []
    try:
        for entry in os.scandir(root):
            if entry.is_dir() and not entry.name.startswith(".") and entry.name not in IGNORE_DIRS:
                dir_path = Path(entry.path)
                has_git = (dir_path / ".git").is_dir()
                has_py = any(dir_path.glob("*.py"))
                has_pkg = (dir_path / "package.json").exists()
                has_docker = (dir_path / "docker-compose.yml").exists() or (dir_path / "Dockerfile").exists()
                has_readme = (dir_path / "README.md").exists()
                
                if has_git or has_py or has_pkg or has_docker or has_readme:
                    detected = detect_project_details(dir_path)
                    detected["is_already_saved"] = str(dir_path.resolve()).rstrip("/") in saved_paths
                    candidates.append(detected)
    except Exception as e:
        print(f"Error scanning {base_path}: {e}")
        
    return candidates

def sync_project_from_disk(project_id: int):
    project = get_project_by_id(project_id)
    if not project:
        return None, "Proyecto no encontrado"
        
    local_path = project.get("local_path")
    if not local_path:
        return None, "El proyecto no tiene una ruta local en disco configurada"
        
    p_path = Path(local_path)
    if not p_path.exists() or not p_path.is_dir():
        return None, f"La carpeta local no existe en disco: {local_path}"
        
    detected = detect_project_details(p_path)
    
    updates = {}
    changes = []
    
    # Check repo URL
    if detected.get("repo_url") and detected["repo_url"] != project.get("repo_url"):
        updates["repo_url"] = detected["repo_url"]
        changes.append("Repositorio Git actualizado")
        
    # Check technical stack
    if detected.get("technical_stack") and detected["technical_stack"] != "Por definir":
        if detected["technical_stack"] != project.get("technical_stack"):
            updates["technical_stack"] = detected["technical_stack"]
            changes.append("Stack tecnológico actualizado")
            
    # Check run command if empty
    if detected.get("run_command") and not project.get("run_command"):
        updates["run_command"] = detected["run_command"]
        changes.append("Comando de arranque actualizado")
        
    # Check tags (merge new tags)
    current_tags = set(project.get("tags") or [])
    new_tags = set(detected.get("tags") or [])
    merged_tags = list(current_tags.union(new_tags))
    if set(merged_tags) != current_tags:
        updates["tags"] = merged_tags
        changes.append("Nuevas etiquetas añadidas")
        
    if updates:
        updated_project = update_project(project_id, updates)
        return updated_project, changes
    else:
        return project, ["Los datos técnicos ya estaban al día"]
