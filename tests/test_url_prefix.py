import sys
from urllib.parse import parse_qs, urlparse
import tempfile
sys.path.insert(0, 'src/pyprojects')
from app.middleware import RedirectPrefixMiddleware, SubpathMiddleware, normalize_base_path
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.main import create_app

def test_subpath():
    app = FastAPI()
    @app.get("/test")
    def t(): return {"ok": True}
    app.add_middleware(SubpathMiddleware, prefix="/pyprojects")
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/pyprojects/test")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    print('subpath OK')


def test_redirect_preserves_mount_prefix():
    app = FastAPI()
    @app.get("/")
    def home(request: Request):
        request.scope["root_path"] = "/pyhost/pyprojects"
        from starlette.responses import RedirectResponse
        return RedirectResponse("/login", status_code=303)
    app.add_middleware(RedirectPrefixMiddleware)
    client = TestClient(app, follow_redirects=False)
    response = client.get("/")
    assert response.headers["location"] == "/pyhost/pyprojects/login"


def test_google_oauth_callback_url_when_mounted(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    with tempfile.TemporaryDirectory() as directory:
        host = FastAPI()
        host.mount("/pyprojects", create_app(
            db_path=f"{directory}/test.db",
            session_secret="test-session-secret",
        ))
        client = TestClient(host, follow_redirects=False)
        response = client.get("/pyprojects/auth/google")
    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    callback = parse_qs(location.query)["redirect_uri"][0]
    assert callback == "http://testserver/pyprojects/auth/google/callback"

if __name__ == '__main__':
    test_subpath()
