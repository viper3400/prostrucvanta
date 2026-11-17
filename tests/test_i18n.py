import sys
import tempfile

sys.path.insert(0, "src/prostrucvanta")

from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.main import create_app


class FormParseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        form = await Request._original_form(request)
        request.state.form_data = dict(form)
        return await call_next(request)


def test_language_can_be_selected_and_persists_for_login_page():
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(db_path=f"{directory}/test.db", session_secret="test-secret")
        app.add_middleware(FormParseMiddleware)
        client = TestClient(app, base_url="https://testserver")

        response = client.get("/login", headers={"Accept-Language": "en-US,en;q=0.9"})
        assert response.status_code == 200
        assert '<html lang="en">' in response.text
        assert "Sign in" in response.text
        assert "ProStrucVanta v0.2.0" in response.text

        csrf_token = client.cookies["csrf_token"]
        response = client.post(
            "/language",
            data={"locale": "de", "csrf_token": csrf_token},
            headers={"Referer": "https://testserver/login"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

        response = client.get("/login", headers={"Accept-Language": "en"})
        assert '<html lang="de">' in response.text
        assert "Anmelden" in response.text


def test_invalid_language_does_not_replace_saved_locale():
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(db_path=f"{directory}/test.db", session_secret="test-secret")
        app.add_middleware(FormParseMiddleware)
        client = TestClient(app, base_url="https://testserver")
        client.get("/login")
        csrf_token = client.cookies["csrf_token"]
        client.post(
            "/language",
            data={"locale": "de", "csrf_token": csrf_token},
            headers={"Referer": "https://testserver/login"},
        )
        client.post(
            "/language",
            data={"locale": "fr", "csrf_token": csrf_token},
            headers={"Referer": "https://testserver/login"},
        )
        response = client.get("/login", headers={"Accept-Language": "en"})
        assert '<html lang="de">' in response.text
