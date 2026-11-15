# Changelog

## 0.1.0
Initial MVP implementation with projects, subprojects, tasks, kanban, Google OAuth, user permissions.

### Features
- Plugin contract `prostrucvanta` with path `/prostrucvanta` and app_factory
- Google OAuth authentication with Authlib, session handling
- SQLite persistence with versioned migrations v001, v002
- Projects CRUD with status, color, dates, owner
- Subprojects CRUD with project relation
- Tasks CRUD with status, priority, assignment, position for Kanban
- Kanban board with drag & drop persistence, filters for project/subproject/priority/assignee/search
- Dashboard metrics
- Admin user management with Global Administration and Project Access permissions, last admin protection
- Reverse proxy support via `PYPROJECTS_BASE_PATH` and SubpathMiddleware
- CSRF protection middleware with token cookie and form injection

### Documentation
- README with Funktionsübersicht, Architektur, Installation, Konfiguration, Google-OAuth-Einrichtung, lokale Entwicklung, PyHost-Integration, Datenbankpfad, Reverse-Proxy-Beispiel, Tests, Wheel Build, Release-Vorgehen
- `.env.example` with all required env vars including `PYPROJECTS_BASE_PATH`
- `AGENTS.md` with project overview and plugin contract

