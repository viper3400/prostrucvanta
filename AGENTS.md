# Agent instructions for PyProjects

## Project overview

PyProjects is a FastAPI plugin for PyHost providing lightweight project and task management with Kanban board.
It follows FeedVanta patterns for plugin registration, Google OAuth, SQLite persistence, session handling, permissions, and packaging.

- Use `uv` for dependency management.
- Python 3.13+ required.
- Do not commit `.env` files or secrets.
- Configuration via environment variables:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `PYPROJECTS_SESSION_SECRET`
  - `PYPROJECTS_SECURE_COOKIES`
  - `PYPROJECTS_DB`
  - `PYPROJECTS_BASE_PATH`
- Database defaults to `data/pyprojects.db`.

## Plugin contract

Entry point `tool_host.plugins` exports `app.plugin:PLUGIN`.
Plugin provides `id`, `name`, `description`, `version`, `path="/pyprojects"`, `app_factory`, optional `lifespan`.

## Tests

Run tests with `uv run pytest`.
Add tests for new behavior, including permissions, migrations, and plugin discovery.

## Commits

Use Conventional Commits: `<type>: <imperative summary>`.
