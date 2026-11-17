import sys
sys.path.insert(0, 'src/prostrucvanta')

import tempfile
import os
import secrets
import base64
import json
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.main import create_app
from app.models import utcnow

# Monkey-patch Starlette Request.form to emulate old property behavior for compatibility
# Starlette 1.x changed request.form to a method, but the app uses request.form.get
# We parse form in middleware and expose via property
Request._original_form = Request.form

class _FormParseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            form_wrapper = Request._original_form(request)
            form = await form_wrapper
            request.state.form_data = dict(form)
        except Exception:
            request.state.form_data = {}
        return await call_next(request)

class _FormProxy:
    def __init__(self, request):
        self._request = request
    def get(self, key, default=None):
        return self._request.state.form_data.get(key, default)

# Replace Request.form with property
Request.form = property(lambda self: _FormProxy(self))

SESSION_SECRET = "test-secret"

def _make_app(db_path, base_path=""):
    app = create_app(db_path=db_path, session_secret=SESSION_SECRET, base_path=base_path)
    # Insert form parse middleware at the front so request.form works
    app.add_middleware(_FormParseMiddleware)
    return app

def _get_csrf_token(client):
    # Trigger a GET to set session and cookie
    client.get("/projects")
    return client._test_csrf_token

def _login_client(client, user_id):
    signer = TimestampSigner(SESSION_SECRET)
    csrf_token = secrets.token_urlsafe(32)
    payload = base64.b64encode(json.dumps({"user_id": user_id, "csrf_token": csrf_token}).encode()).decode()
    signed = signer.sign(payload.encode()).decode()
    client.cookies.set("session", signed)
    client.cookies.set("csrf_token", csrf_token)
    client._test_csrf_token = csrf_token
    return client

def _create_user(app, perm="Project Access"):
    db = app.state.db
    with db.connect() as conn:
        now = utcnow()
        conn.execute(
            "INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
            (f"sub_{perm}", f"{perm.replace(' ','_')}@test", "Test User", now, now)
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO user_permissions(user_id,permission,granted_at) VALUES(?,?,?)",
            (uid, perm, now)
        )
    return uid

def _create_admin(app):
    db = app.state.db
    with db.connect() as conn:
        now = utcnow()
        conn.execute(
            "INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
            ("sub_admin", "admin@test", "Admin", now, now)
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO user_permissions(user_id,permission,granted_at) VALUES(?,?,?)",
            (uid, "Global Administration", now)
        )
    return uid

def test_unauthenticated_access():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        r = client.get("/projects")
        assert r.status_code == 401

def test_access_without_permission():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                         ("sub_noperm","noperm@test","NoPerm",now,now))
            uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        r = client.get("/projects")
        assert r.status_code == 403

def test_create_and_edit_project():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        # create
        r = client.post("/projects", data={"name":"P1","description":"desc","status":"Aktiv","color":"#111","csrf_token":token})
        assert r.status_code == 303
        # verify in db
        with app.state.db.connect() as conn:
            proj = conn.execute("SELECT id,name FROM projects WHERE name=?", ("P1",)).fetchone()
            assert proj is not None
            pid = proj["id"]
        # edit
        r = client.post(f"/projects/{pid}/edit", data={"name":"P1 edited","description":"new","status":"Pausiert","color":"#222","start_date":"","target_date":"","csrf_token":token})
        assert r.status_code == 303
        with app.state.db.connect() as conn:
            proj2 = conn.execute("SELECT name,status FROM projects WHERE id=?", (pid,)).fetchone()
            assert proj2["name"] == "P1 edited"
            assert proj2["status"] == "Pausiert"

def test_create_and_edit_subproject():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post(f"/projects/{pid}/subprojects", data={"name":"S1","description":"sub","status":"Aktiv","csrf_token":token})
        assert r.status_code == 303
        with app.state.db.connect() as conn:
            sub = conn.execute("SELECT id,name FROM subprojects WHERE project_id=?", (pid,)).fetchone()
            assert sub["name"] == "S1"
            sid = sub["id"]
        r = client.post(f"/subprojects/{sid}/edit", data={"name":"S1 edited","description":"","status":"Aktiv","project_id":str(pid),"csrf_token":token})
        assert r.status_code == 303
        with app.state.db.connect() as conn:
            sub2 = conn.execute("SELECT name FROM subprojects WHERE id=?", (sid,)).fetchone()
            assert sub2["name"] == "S1 edited"

def test_create_task_and_assignment():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                         (pid,"S", "Aktiv", now, now))
            sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post("/tasks", data={"title":"T1","project_id":str(pid),"subproject_id":str(sid),"status":"Backlog","priority":"Normal","csrf_token":token})
        assert r.status_code == 303
        with app.state.db.connect() as conn:
            task = conn.execute("SELECT id,title,project_id,subproject_id FROM tasks WHERE title=?", ("T1",)).fetchone()
            assert task["project_id"] == pid and task["subproject_id"] == sid
            tid = task["id"]
        r = client.post(f"/tasks/{tid}/edit", data={"title":"T1","project_id":str(pid),"subproject_id":"","status":"Backlog","priority":"Normal","csrf_token":token})
        assert r.status_code == 303
        with app.state.db.connect() as conn:
            task2 = conn.execute("SELECT subproject_id FROM tasks WHERE id=?", (tid,)).fetchone()
            assert task2["subproject_id"] is None

def test_task_status_change():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id) VALUES(?,?,?,?,?,?,?)",
                         ("T",pid,"Backlog","Normal",now,now,uid))
            tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post(f"/tasks/{tid}/update", data={"status":"Offen","csrf_token":token})
        assert r.status_code == 204
        with app.state.db.connect() as conn:
            t = conn.execute("SELECT status FROM tasks WHERE id=?", (tid,)).fetchone()
            assert t["status"] == "Offen"

def test_kanban_sorting():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id,position) VALUES(?,?,?,?,?,?,?,?)",
                         ("T1",pid,"Backlog","Normal",now,now,uid,0))
            t1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id,position) VALUES(?,?,?,?,?,?,?,?)",
                         ("T2",pid,"Backlog","Normal",now,now,uid,1))
            t2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post("/kanban/update", data={"id":str(t2),"status":"Offen","position":"0","priority":"Normal","assignee_id":"","csrf_token":token})
        assert r.status_code == 204
        r2 = client.post("/kanban/update", data={"id":str(t1),"status":"Offen","position":"1","priority":"Normal","assignee_id":"","csrf_token":token})
        assert r2.status_code == 204
        with app.state.db.connect() as conn:
            rows = conn.execute("SELECT id,position,status FROM tasks WHERE project_id=? ORDER BY position", (pid,)).fetchall()
            assert rows[0]["id"] == t2 and rows[0]["position"] == 0
            assert rows[1]["id"] == t1 and rows[1]["position"] == 1

def test_kanban_subproject_filter_is_scoped_to_selected_project():
    with tempfile.TemporaryDirectory() as td:
        app = _make_app(os.path.join(td, "db.sqlite"))
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            for name in ("Project A", "Project B"):
                conn.execute(
                    "INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                    (name, "Aktiv", "#000", now, now, uid),
                )
            project_a, project_b = [
                row["id"] for row in conn.execute(
                    "SELECT id FROM projects ORDER BY id"
                ).fetchall()
            ]
            conn.execute(
                "INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                (project_a, "Subproject A", "Aktiv", now, now),
            )
            subproject_a = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                (project_b, "Subproject B", "Aktiv", now, now),
            )

        client = TestClient(app, raise_server_exceptions=False)
        _login_client(client, uid)
        response = client.get(f"/kanban?project={project_a}")

        assert response.status_code == 200
        assert f'value="{subproject_a}"' in response.text
        assert ">Subproject A</option>" in response.text
        assert ">Subproject B</option>" not in response.text

def test_task_move_consistency():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id,position) VALUES(?,?,?,?,?,?,?,?)",
                         ("T",pid,"Backlog","Normal",now,now,uid,0))
            tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post("/kanban/update", data={"id":str(tid),"status":"In Bearbeitung","position":"0","priority":"Hoch","assignee_id":"","csrf_token":token})
        assert r.status_code == 204
        with app.state.db.connect() as conn:
            t = conn.execute("SELECT status,priority,position FROM tasks WHERE id=?", (tid,)).fetchone()
            assert t["status"] == "In Bearbeitung"
            assert t["priority"] == "Hoch"
            assert t["position"] == 0

def test_admin_requires_admin():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app, perm="Project Access")
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        r = client.get("/admin")
        assert r.status_code == 403

def test_last_admin_protection_http():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        admin_id = _create_admin(app)
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, admin_id)
        token = _get_csrf_token(client)
        # try to remove own admin permission
        r = client.post(f"/admin/users/{admin_id}/global-administration", data={"enabled":"0","csrf_token":token})
        assert r.status_code == 409

def test_invalid_input_project_name():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post("/projects", data={"name":"","description":"","csrf_token":token})
        assert r.status_code == 400

def test_invalid_input_task_missing_title():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post("/tasks", data={"title":"","project_id":str(pid),"csrf_token":token})
        assert r.status_code == 400

def test_delete_project_with_dependencies_409():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        admin_id = _create_admin(app)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,admin_id))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                         (pid,"S","Aktiv",now,now))
            conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id) VALUES(?,?,?,?,?,?,?)",
                         ("T",pid,"Backlog","Normal",now,now,admin_id))
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, admin_id)
        token = _get_csrf_token(client)
        r = client.post(f"/projects/{pid}/delete", data={"csrf_token":token})
        assert r.status_code == 409

def test_delete_subproject_with_tasks_409():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path)
        uid = _create_user(app)
        with app.state.db.connect() as conn:
            now = utcnow()
            conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                         ("P","Aktiv","#000",now,now,uid))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                         (pid,"S","Aktiv",now,now))
            sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO tasks(title,project_id,subproject_id,status,priority,created_at,updated_at,creator_id) VALUES(?,?,?,?,?,?,?,?)",
                         ("T",pid,sid,"Backlog","Normal",now,now,uid))
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        token = _get_csrf_token(client)
        r = client.post(f"/subprojects/{sid}/delete", data={"csrf_token":token})
        assert r.status_code == 409

def test_url_prefix_end_to_end():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "db.sqlite")
        app = _make_app(db_path, base_path="/prostrucvanta")
        uid = _create_user(app)
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        _login_client(client, uid)
        r = client.get("/prostrucvanta/projects")
        assert r.status_code == 200
        # without prefix should be 404
        r2 = client.get("/projects")
        assert r2.status_code == 404

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
