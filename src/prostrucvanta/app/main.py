import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from .middleware import RedirectPrefixMiddleware, SubpathMiddleware
from .security import CsrfMiddleware

from .db import Database
from .auth import AuthService, GLOBAL_ADMINISTRATION, PROJECT_ACCESS
from .models import utcnow
from .version import APP_VERSION
from .i18n import TRANSLATIONS, translate

BASE_DIR = Path(__file__).parent
load_dotenv()

async def _get_form(request: Request):
    # Support test middleware that stores parsed form in request.state.form_data
    if hasattr(request.state, "form_data"):
        return request.state.form_data
    form = request.form
    if callable(form):
        return await form()
    return form

def create_app(db_path: str | None = None, session_secret: str | None = None, base_path: str = "") -> FastAPI:
    db = Database(db_path or os.getenv("PYPROJECTS_DB", "data/pyprojects.db"))
    db.initialize()
    auth_service = AuthService(db)

    app = FastAPI(title="ProStrucVanta", version=APP_VERSION)
    app.add_middleware(RedirectPrefixMiddleware)
    app.add_middleware(CsrfMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret or os.getenv("PYPROJECTS_SESSION_SECRET") or secrets.token_urlsafe(32),
        same_site="lax",
        https_only=os.getenv("PYPROJECTS_SECURE_COOKIES", "false").lower() in {"1","true","yes"},
    )
    # Support reverse proxy prefix
    base_path = os.getenv("PYPROJECTS_BASE_PATH") or base_path
    if base_path:
        app.add_middleware(SubpathMiddleware, prefix=base_path)
    app.state.db = db
    app.state.auth_service = auth_service

    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    translations = TRANSLATIONS
    templates.env.globals["translate"] = translate
    def locale_for(request: Request) -> str:
        saved = request.session.get("locale")
        if saved in translations:
            return saved
        preferences = []
        for index, item in enumerate(request.headers.get("accept-language", "").split(",")):
            parts = item.strip().lower().split(";")
            language = parts[0]
            try:
                quality = float(parts[1].removeprefix("q=")) if len(parts) > 1 else 1.0
            except ValueError:
                quality = 0.0
            preferences.append((quality, -index, language))
        for _, _, language in sorted(preferences, reverse=True):
            if language.startswith("de"):
                return "de"
            if language.startswith("en"):
                return "en"
        return "de"
    templates.env.globals["locale_for"] = locale_for
    @app.post("/language")
    async def set_language(request: Request):
        form = await _get_form(request)
        locale = form.get("locale")
        if locale in translations:
            request.session["locale"] = locale
        referer = request.headers.get("referer", "/")
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        target = parsed.path if parsed.netloc == request.url.netloc else "/"
        if parsed.query:
            target += "?" + parsed.query
        return RedirectResponse(target, status_code=303)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    oauth = OAuth()
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if client_id and client_secret:
        oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    def current_user(request: Request):
        uid = request.session.get("user_id")
        return auth_service.get_user(int(uid)) if uid else None

    def require_login(request: Request):
        user = current_user(request)
        if not user:
            raise HTTPException(401, "Anmeldung erforderlich")
        return user

    def require_admin(request: Request):
        user = require_login(request)
        if GLOBAL_ADMINISTRATION not in user["permissions"]:
            raise HTTPException(403, "Global Administration erforderlich")
        return user

    def require_access(request: Request):
        user = require_login(request)
        if GLOBAL_ADMINISTRATION in user["permissions"] or PROJECT_ACCESS in user["permissions"]:
            return user
        raise HTTPException(403, "Project Access erforderlich")

    def get_user_id(user):
        return user["id"]

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        user = current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        with db.connect() as conn:
            active_projects = conn.execute("SELECT COUNT(*) FROM projects WHERE status='Aktiv'").fetchone()[0]
            subprojects = conn.execute("SELECT COUNT(*) FROM subprojects").fetchone()[0]
            open_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('Offen','In Bearbeitung')").fetchone()[0]
            overdue = conn.execute("SELECT COUNT(*) FROM tasks WHERE due_date IS NOT NULL AND due_date < datetime('now') AND status != 'Erledigt'").fetchone()[0]
            recent = conn.execute("SELECT id,title,updated_at FROM tasks ORDER BY updated_at DESC LIMIT 5").fetchall()
        return templates.TemplateResponse(request, "index.html", {
            "current_user": user,
            "active_projects": active_projects,
            "subprojects": subprojects,
            "open_tasks": open_tasks,
            "overdue": overdue,
            "recent": [dict(r) for r in recent],
        })

    @app.get("/login", response_class=HTMLResponse)
    def login(request: Request):
        return templates.TemplateResponse(request, "login.html", {"google_configured": bool(client_id and client_secret)})

    @app.get("/auth/google")
    async def auth_google(request: Request):
        if not client_id or not client_secret:
            raise HTTPException(503, "Google-Anmeldung nicht konfiguriert")
        root_path = request.scope.get("root_path", "").rstrip("/")
        callback_path = app.url_path_for("auth_callback")
        redirect_uri = str(
            request.url.replace(
                path=f"{root_path}{callback_path}",
                query="",
                fragment="",
            )
        )
        return await oauth.google.authorize_redirect(request, redirect_uri)

    @app.get("/auth/google/callback")
    async def auth_callback(request: Request):
        if not client_id or not client_secret:
            raise HTTPException(503, "Google-Anmeldung nicht konfiguriert")
        try:
            token = await oauth.google.authorize_access_token(request)
            profile = token.get("userinfo") or await oauth.google.userinfo(token=token)
            user = auth_service.login_google_user(dict(profile))
        except (OAuthError, ValueError) as exc:
            raise HTTPException(400, f"Google-Anmeldung fehlgeschlagen: {exc}")
        request.session.clear()
        request.session["user_id"] = user["id"]
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Projects
    @app.get("/projects", response_class=HTMLResponse)
    def projects_list(request: Request, user=Depends(require_access)):
        with db.connect() as conn:
            projects = [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")]
            for p in projects:
                sub = conn.execute("SELECT id,name,status,color,description,created_at,updated_at,start_date,target_date FROM subprojects WHERE project_id=? ORDER BY name", (p["id"],)).fetchall()
                p["subprojects"] = [dict(s) for s in sub]
                p["task_count"] = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id=?", (p["id"],)).fetchone()[0]
                p["done"] = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='Erledigt'", (p["id"],)).fetchone()[0]
                p["progress"] = round(p["done"]/p["task_count"]*100) if p["task_count"] else 0
        return templates.TemplateResponse(request, "projects.html", {"current_user": user, "projects": projects})

    @app.post("/projects")
    async def create_project(request: Request, user=Depends(require_access)):
        form = await _get_form(request)
        name = form.get("name","").strip()
        description = form.get("description","")
        status = form.get("status","Aktiv")
        color = form.get("color","#3b82f6")
        start_date = form.get("start_date") or None
        target_date = form.get("target_date") or None
        if not name:
            raise HTTPException(400, "Name erforderlich")
        now = utcnow()
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO projects(name,description,status,color,created_at,updated_at,start_date,target_date,owner_id) VALUES(?,?,?,?,?,?,?,?,?)",
                (name, description, status, color, now, now, start_date, target_date, get_user_id(user))
            )
        return RedirectResponse("/projects", status_code=303)

    @app.post("/projects/{project_id}/edit")
    async def edit_project(request: Request, project_id: int, user=Depends(require_access)):
        form = await _get_form(request)
        name = form.get("name","").strip()
        description = form.get("description","")
        status = form.get("status")
        color = form.get("color")
        start_date = form.get("start_date")
        target_date = form.get("target_date")
        if not name:
            raise HTTPException(400, "Name erforderlich")
        now = utcnow()
        with db.connect() as conn:
            conn.execute(
                "UPDATE projects SET name=?, description=?, status=?, color=?, start_date=?, target_date=?, updated_at=? WHERE id=?",
                (name, description, status, color, start_date, target_date, now, project_id)
            )
        return RedirectResponse("/projects", status_code=303)

    @app.post("/projects/{project_id}/archive")
    async def archive_project(request: Request, project_id: int, user=Depends(require_access)):
        now = utcnow()
        with db.connect() as conn:
            conn.execute("UPDATE projects SET status='Archiviert', updated_at=? WHERE id=?", (now, project_id))
        return RedirectResponse("/projects", status_code=303)

    @app.post("/projects/{project_id}/delete")
    async def delete_project(request: Request, project_id: int, user=Depends(require_admin)):
        with db.connect() as conn:
            proj = conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone()
            if not proj:
                raise HTTPException(404, "Projekt nicht gefunden")
            sub_count = conn.execute("SELECT COUNT(*) FROM subprojects WHERE project_id=?", (project_id,)).fetchone()[0]
            task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id=?", (project_id,)).fetchone()[0]
            if sub_count > 0 or task_count > 0:
                raise HTTPException(409, f"Projekt kann nicht gelöscht werden: {sub_count} Unterprojekte und {task_count} Tasks vorhanden. Bitte zuerst entfernen oder archivieren.")
            conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
        return RedirectResponse("/projects", status_code=303)

    # Subprojects
    @app.post("/projects/{project_id}/subprojects")
    async def create_subproject(request: Request, project_id: int, user=Depends(require_access)):
        form = await _get_form(request)
        name = form.get("name","").strip()
        description = form.get("description","")
        status = form.get("status","Aktiv")
        color = form.get("color") or None
        start_date = form.get("start_date") or None
        target_date = form.get("target_date") or None
        if not name:
            raise HTTPException(400, "Name erforderlich")
        now = utcnow()
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO subprojects(project_id,name,description,status,color,created_at,updated_at,start_date,target_date) VALUES(?,?,?,?,?,?,?,?,?)",
                (project_id, name, description, status, color, now, now, start_date, target_date)
            )
        return RedirectResponse("/projects", status_code=303)

    @app.post("/subprojects/{sub_id}/edit")
    async def edit_subproject(request: Request, sub_id: int, user=Depends(require_access)):
        form = await _get_form(request)
        name = form.get("name","").strip()
        description = form.get("description","")
        status = form.get("status")
        color = form.get("color")
        start_date = form.get("start_date")
        target_date = form.get("target_date")
        project_id = form.get("project_id")
        if not name:
            raise HTTPException(400, "Name erforderlich")
        now = utcnow()
        with db.connect() as conn:
            conn.execute(
                "UPDATE subprojects SET name=?, description=?, status=?, color=?, start_date=?, target_date=?, project_id=?, updated_at=? WHERE id=?",
                (name, description, status, color, start_date, target_date, int(project_id) if project_id else None, now, sub_id)
            )
        return RedirectResponse("/projects", status_code=303)

    @app.post("/subprojects/{sub_id}/archive")
    async def archive_subproject(request: Request, sub_id: int, user=Depends(require_access)):
        now = utcnow()
        with db.connect() as conn:
            conn.execute("UPDATE subprojects SET status='Archiviert', updated_at=? WHERE id=?", (now, sub_id))
        return RedirectResponse("/projects", status_code=303)

    @app.post("/subprojects/{sub_id}/delete")
    async def delete_subproject(request: Request, sub_id: int, user=Depends(require_access)):
        with db.connect() as conn:
            task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE subproject_id=?", (sub_id,)).fetchone()[0]
            if task_count > 0:
                raise HTTPException(409, f"Unterprojekt kann nicht gelöscht werden: {task_count} Tasks vorhanden. Bitte zuerst entfernen oder archivieren.")
            conn.execute("DELETE FROM subprojects WHERE id=?", (sub_id,))
        return RedirectResponse("/projects", status_code=303)

    # Tasks
    @app.get("/tasks", response_class=HTMLResponse)
    def tasks_list(request: Request, user=Depends(require_access)):
        with db.connect() as conn:
            projects = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, name FROM projects ORDER BY name"
                )
            ]
            subprojects = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, project_id, name FROM subprojects ORDER BY name"
                )
            ]
            tasks = [dict(r) for r in conn.execute("""
                SELECT t.*, p.name as project_name, p.color as project_color,
                       s.name as subproject_name, u.name as assignee_name
                FROM tasks t
                JOIN projects p ON p.id=t.project_id
                LEFT JOIN subprojects s ON s.id=t.subproject_id
                LEFT JOIN users u ON u.id=t.assignee_id
                ORDER BY t.updated_at DESC
            """)]
        return templates.TemplateResponse(
            request,
            "tasks.html",
            {
                "current_user": user,
                "tasks": tasks,
                "projects": projects,
                "subprojects": subprojects,
            },
        )

    @app.post("/tasks")
    async def create_task(request: Request, user=Depends(require_access)):
        form = await _get_form(request)
        title = form.get("title","").strip()
        description = form.get("description","")
        project_id = int(form.get("project_id") or 0)
        subproject_id = form.get("subproject_id")
        subproject_id = int(subproject_id) if subproject_id else None
        status = form.get("status","Backlog")
        priority = form.get("priority","Normal")
        due_date = form.get("due_date") or None
        start_date = form.get("start_date") or None
        assignee_id = form.get("assignee_id")
        assignee_id = int(assignee_id) if assignee_id else None
        if not title or not project_id:
            raise HTTPException(400, "Titel und Projekt erforderlich")
        now = utcnow()
        with db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO tasks(title,description,project_id,subproject_id,status,priority,created_at,updated_at,due_date,start_date,assignee_id,creator_id,position) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (title, description, project_id, subproject_id, status, priority, now, now, due_date, start_date, assignee_id, get_user_id(user), 0)
            )
        return RedirectResponse("/tasks", status_code=303)

    @app.post("/tasks/{task_id}/edit")
    async def edit_task(request: Request, task_id: int, user=Depends(require_access)):
        form = await _get_form(request)
        title = form.get("title","").strip()
        description = form.get("description","")
        project_id = form.get("project_id")
        subproject_id = form.get("subproject_id")
        status = form.get("status")
        priority = form.get("priority")
        due_date = form.get("due_date")
        start_date = form.get("start_date")
        assignee_id = form.get("assignee_id")
        if not title or not project_id:
            raise HTTPException(400, "Titel und Projekt erforderlich")
        now = utcnow()
        with db.connect() as conn:
            conn.execute(
                "UPDATE tasks SET title=?, description=?, project_id=?, subproject_id=?, status=?, priority=?, due_date=?, start_date=?, assignee_id=?, updated_at=? WHERE id=?",
                (title, description, int(project_id), int(subproject_id) if subproject_id else None, status, priority, due_date, start_date, int(assignee_id) if assignee_id else None, now, task_id)
            )
        return RedirectResponse("/tasks", status_code=303)

    @app.post("/tasks/{task_id}/duplicate")
    async def duplicate_task(request: Request, task_id: int, user=Depends(require_access)):
        with db.connect() as conn:
            t = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not t:
                raise HTTPException(404, "Task nicht gefunden")
            now = utcnow()
            conn.execute(
                "INSERT INTO tasks(title,description,project_id,subproject_id,status,priority,created_at,updated_at,due_date,start_date,assignee_id,creator_id,position) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (t["title"] + " (Kopie)", t["description"], t["project_id"], t["subproject_id"], "Backlog", t["priority"], now, now, t["due_date"], t["start_date"], None, get_user_id(user), 0)
            )
        return RedirectResponse("/tasks", status_code=303)

    @app.post("/tasks/{task_id}/update")
    async def update_task(request: Request, task_id: int, user=Depends(require_access)):
        form = await _get_form(request)
        status = form.get("status")
        priority = form.get("priority")
        assignee_id = form.get("assignee_id")
        due_date = form.get("due_date")
        position = form.get("position")
        now = utcnow()
        with db.connect() as conn:
            if status:
                conn.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?", (status, now, task_id))
            if priority:
                conn.execute("UPDATE tasks SET priority=?, updated_at=? WHERE id=?", (priority, now, task_id))
            if assignee_id is not None:
                conn.execute("UPDATE tasks SET assignee_id=?, updated_at=? WHERE id=?", (int(assignee_id) if assignee_id else None, now, task_id))
            if due_date is not None:
                conn.execute("UPDATE tasks SET due_date=?, updated_at=? WHERE id=?", (due_date, now, task_id))
            if position is not None:
                conn.execute("UPDATE tasks SET position=?, updated_at=? WHERE id=?", (int(position), now, task_id))
        return Response(status_code=204)

    @app.post("/tasks/{task_id}/delete")
    async def delete_task(request: Request, task_id: int, user=Depends(require_access)):
        with db.connect() as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return RedirectResponse("/tasks", status_code=303)

    # Kanban
    @app.get("/kanban", response_class=HTMLResponse)
    def kanban(request: Request, user=Depends(require_access)):
        project_id = request.query_params.get("project")
        subproject_id = request.query_params.get("subproject")
        priority = request.query_params.get("priority")
        assignee_id = request.query_params.get("assignee")
        search = request.query_params.get("search","").strip()
        with db.connect() as conn:
            if subproject_id and not project_id:
                subproject_project = conn.execute(
                    "SELECT project_id FROM subprojects WHERE id=?",
                    (int(subproject_id),),
                ).fetchone()
                if subproject_project:
                    project_id = str(subproject_project["project_id"])

            subproject_sql = "SELECT id,name,project_id FROM subprojects"
            subproject_params = []
            if project_id:
                subproject_sql += " WHERE project_id=?"
                subproject_params.append(int(project_id))
            subproject_sql += " ORDER BY name"
            subprojects = [dict(r) for r in conn.execute(subproject_sql, subproject_params)]
            valid_subproject_ids = {sp["id"] for sp in subprojects}
            if subproject_id and int(subproject_id) not in valid_subproject_ids:
                subproject_id = None

            sql = """
                SELECT t.*, p.name as project_name, s.name as subproject_name, u.name as assignee_name, p.color as project_color
                FROM tasks t
                JOIN projects p ON p.id=t.project_id
                LEFT JOIN subprojects s ON s.id=t.subproject_id
                LEFT JOIN users u ON u.id=t.assignee_id
                WHERE 1=1
            """
            params = []
            if project_id:
                sql += " AND t.project_id=?"
                params.append(int(project_id))
            if subproject_id:
                sql += " AND t.subproject_id=?"
                params.append(int(subproject_id))
            if priority:
                sql += " AND t.priority=?"
                params.append(priority)
            if assignee_id:
                sql += " AND t.assignee_id=?"
                params.append(int(assignee_id))
            if search:
                sql += " AND t.title LIKE ?"
                params.append(f"%{search}%")
            sql += " ORDER BY t.position, t.updated_at"
            tasks = [dict(r) for r in conn.execute(sql, params)]
            projects = [dict(r) for r in conn.execute("SELECT id,name FROM projects")]
            users = [dict(r) for r in conn.execute("SELECT id,name FROM users")]
        return templates.TemplateResponse(request, "kanban.html", {
            "current_user": user,
            "tasks": tasks,
            "projects": projects,
            "users": users,
            "subprojects": subprojects,
            "statuses": ["Backlog","Offen","In Bearbeitung","Blockiert","Erledigt"],
            "priorities": ["Niedrig","Normal","Hoch","Kritisch"],
            "selected_project": int(project_id) if project_id else None,
            "selected_subproject": int(subproject_id) if subproject_id else None,
            "selected_priority": priority,
            "selected_assignee": int(assignee_id) if assignee_id else None,
            "search": search,
        })

    @app.post("/kanban/update")
    async def kanban_update(request: Request, user=Depends(require_access)):
        form = await _get_form(request)
        task_id = int(form.get("id"))
        status = form.get("status")
        position = int(form.get("position",0))
        priority = form.get("priority")
        assignee_id = form.get("assignee_id")
        # CSRF token check for API-like endpoint
        csrf_token = request.headers.get("X-CSRF-Token") or form.get("csrf_token")
        session_token = request.session.get("csrf_token")
        if csrf_token and session_token and csrf_token != session_token:
            raise HTTPException(403, "CSRF token mismatch")
        now = utcnow()
        with db.connect() as conn:
            conn.execute(
                "UPDATE tasks SET status=?, position=?, priority=?, assignee_id=?, updated_at=? WHERE id=?",
                (status, position, priority or None, int(assignee_id) if assignee_id else None, now, task_id)
            )
        return Response(status_code=204)

    # Admin
    @app.get("/admin", response_class=HTMLResponse)
    def admin_index(request: Request, user=Depends(require_admin)):
        return templates.TemplateResponse(request, "admin.html", {"current_user": user})

    @app.get("/admin/users", response_class=HTMLResponse)
    def users_admin(request: Request, user=Depends(require_admin)):
        users = auth_service.list_users()
        return templates.TemplateResponse(request, "users.html", {"current_user": user, "users": users})

    @app.post("/admin/users/{user_id}/project-access")
    async def set_project_access(request: Request, user_id: int, user=Depends(require_admin)):
        form = await _get_form(request)
        enabled = form.get("enabled") == "1"
        auth_service.set_permission(user_id, PROJECT_ACCESS, enabled)
        return RedirectResponse("/admin/users", status_code=303)

    @app.post("/admin/users/{user_id}/global-administration")
    async def set_global_admin(request: Request, user_id: int, user=Depends(require_admin)):
        form = await _get_form(request)
        enabled = form.get("enabled") == "1"
        try:
            auth_service.set_permission(user_id, GLOBAL_ADMINISTRATION, enabled)
        except ValueError as e:
            raise HTTPException(409, str(e))
        return RedirectResponse("/admin/users", status_code=303)

    # API endpoints for Kanban drag-drop and filters
    @app.get("/api/tasks")
    def api_tasks(project_id: int | None = None, subproject_id: int | None = None, status: str | None = None, priority: str | None = None, assignee_id: int | None = None, search: str | None = None, user=Depends(require_access)):
        with db.connect() as conn:
            sql = "SELECT t.*, p.name as project_name FROM tasks t JOIN projects p ON p.id=t.project_id WHERE 1=1"
            params = []
            if project_id:
                sql += " AND t.project_id=?"
                params.append(project_id)
            if subproject_id:
                sql += " AND t.subproject_id=?"
                params.append(subproject_id)
            if status:
                sql += " AND t.status=?"
                params.append(status)
            if priority:
                sql += " AND t.priority=?"
                params.append(priority)
            if assignee_id:
                sql += " AND t.assignee_id=?"
                params.append(assignee_id)
            if search:
                sql += " AND t.title LIKE ?"
                params.append(f"%{search}%")
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    return app
