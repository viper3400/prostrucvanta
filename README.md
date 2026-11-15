# PyProjects

Lightweight project and task management plugin for PyHost.

## Funktionsübersicht

PyProjects bietet eine schlanke Projektverwaltung mit Hauptprojekten, Unterprojekten und Tasks sowie einem interaktiven Kanban-Board.

- Hauptprojekte mit Status, Farbe, Start-/Zieldatum und Eigentümer
- Unterprojekte pro Hauptprojekt mit eigenem Status und Farbe
- Tasks mit Titel, Beschreibung, Status, Priorität, Fälligkeit, Zuordnung und Sortierposition
- Projektauswahl nach Namen beim Erstellen von Tasks
- Kanban-Board mit Drag & Drop, Filtern nach Projekt, Unterprojekt, Priorität, Bearbeiter und Suche
- Dashboard mit Metriken: aktive Projekte, Unterprojekte, offene Tasks, überfällige Tasks, kürzlich bearbeitete Tasks
- Google OAuth Anmeldung, Session-basiert
- Benutzerverwaltung mit Berechtigungen `Global Administration` und `Project Access`, Schutz des letzten Administrators
- SQLite Persistenz mit versionierten Migrationen
- Plugin-Integration in PyHost unter `/pyprojects`, Reverse-Proxy-Unterstützung

## Architektur

- **FastAPI** für HTTP-Routen und Plugin-Factory
- **Jinja2** Templates mit Tailwind CSS, Vanilla JavaScript
- **SQLite** mit `PRAGMA user_version` Migrationen
- **Authlib** für Google OAuth OpenID Connect
- **Starlette SessionMiddleware** für sichere Session-Cookies
- **SubpathMiddleware** für Reverse-Proxy-Prefixe
- Plugin-Vertrag über Entry-Point `tool_host.plugins` → `app.plugin:PLUGIN`

Modularer Aufbau:
- `app/main.py` – App Factory, Routen, Middleware
- `app/db.py` – Datenbankverbindung und Migrationen
- `app/auth.py` – Google Login, Berechtigungen
- `app/middleware.py` – Subpath handling
- `app/security.py` – CSRF Middleware
- `app/templates/` – Jinja2 Views

## Installation in PyHost

Für die lokale Entwicklung müssen `py-projects` und `pyhost` als Geschwisterverzeichnisse ausgecheckt sein. PyProjects wird in die virtuelle Umgebung von PyHost installiert:

```bash
uv sync --extra test
uv sync --project ../pyhost --all-packages
uv pip install --python ../pyhost/.venv/bin/python -e .
uv run --project ../pyhost pyhost --reload
```

Der PyHost-Server ist danach standardmäßig unter `http://127.0.0.1:8000` erreichbar; PyProjects wird unter `/pyprojects/` eingebunden. Wenn Port 8000 belegt ist, kann PyHost beispielsweise mit `--port 8001` gestartet werden.

Abhängigkeiten werden über `pyproject.toml` verwaltet. Python 3.13+ erforderlich. PyProjects implementiert den PyHost-Pluginvertrag strukturell und benötigt PyHost nicht als Projektabhängigkeit.

## Konfiguration

Kopiere `.env.example` nach `.env`:

```bash
cp .env.example .env
```

Variablen:
- `GOOGLE_CLIENT_ID` – Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` – Google OAuth Client Secret
- `PYPROJECTS_SESSION_SECRET` – Zufälliger 32-Byte Secret für Session Cookies
- `PYPROJECTS_SECURE_COOKIES` – `true`/`false` für HTTPS-only Cookies
- `PYPROJECTS_DB` – Pfad zur SQLite Datenbank, Standard `data/pyprojects.db`
- `PYPROJECTS_BASE_PATH` – Optionaler Reverse-Proxy-Prefix, z.B. `/tools/pyprojects`

## Google-OAuth-Einrichtung

1. In Google Cloud Console ein OAuth 2.0 Client erstellen
2. Authorized Redirect URI setzen auf die vollständige Callback-Adresse. Lokal ohne Host-Präfix ist das `http://localhost:8000/pyprojects/auth/google/callback`. Mit PyHost-Präfix `/pyhost` lautet sie `http://localhost:8000/pyhost/pyprojects/auth/google/callback`.
3. Client ID und Secret in `.env` eintragen
4. Plugin starten und unter `/pyprojects/login` (mit Host-Präfix `/pyhost`: `/pyhost/pyprojects/login`) **Anmelden mit Google** wählen.

Erster Login legt Benutzer an und vergibt automatisch `Global Administration`.

## Eigenständiger Start (ohne PyHost)

```bash
uv run uvicorn app.main:create_app --factory --reload
```

App läuft auf `http://localhost:8000`. `PYPROJECTS_BASE_PATH` ist nur für einen Reverse-Proxy-Präfix beim eigenständigen Betrieb gedacht. Bei PyHost übernimmt PyHost den gemeinsamen Präfix über `TOOL_HOST_BASE_PATH` oder `X-Forwarded-Prefix`; `PYPROJECTS_BASE_PATH` dafür nicht setzen.

## PyHost-Integration

Entry Point in `pyproject.toml`:

```toml
[project.entry-points."tool_host.plugins"]
pyprojects = "app.plugin:PLUGIN"
```

Plugin wird automatisch entdeckt, Pfad `/pyprojects`, App Factory liefert FastAPI App.

## Datenbankpfad

Standard `data/pyprojects.db`. Überschreibbar via `PYPROJECTS_DB`. Migrationen laufen automatisch beim Start via `Database.initialize()`.

## Reverse-Proxy-Beispiel

Nginx:
```nginx
location /tools/pyprojects/ {
    proxy_pass http://pyhost/;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Beim eigenständigen Betrieb kann zusätzlich die Plugin-Umgebung gesetzt werden:
```
PYPROJECTS_BASE_PATH=/tools/pyprojects
```

Bei PyHost stattdessen den gemeinsamen Host-Präfix konfigurieren (`TOOL_HOST_BASE_PATH=/tools` oder den vom vertrauenswürdigen Proxy gelieferten Header `X-Forwarded-Prefix: /tools`). Der Plugin-Pfad `/pyprojects` wird vom Host ergänzt.

## Tests

```bash
uv run pytest
```

Tests decken ab:
1. Plugin-Erkennung
2. CRUD Hauptprojekte/Unterprojekte/Tasks
3. Task-Zuordnung und Statusänderungen
4. Kanban-Sortierung und Konsistenz
5. Berechtigungen, Zugriff ohne Anmeldung
6. Administratorrechte, Schutz letzter Admin
7. Datenbankmigrationen
8. Ungültige Eingaben
9. URL-Prefix Betrieb
10. Fehlerfälle und konkurrierende Änderungen

## Wheel Build

```bash
uv build
```

Erzeugt `dist/pyprojects-0.1.0-py3-none-any.whl`.

## Release-Vorgehen

1. Version in `pyproject.toml` und `src/pyprojects/app/version.py` erhöhen
2. `CHANGES.md` aktualisieren
3. Tests laufen lassen: `uv run pytest`
4. Build: `uv build`
5. Wheel in PyPI oder internem Index veröffentlichen
6. Conventional Commits verwenden: `feat: ...`, `fix: ...`

## Lizenz

Siehe Repository.
