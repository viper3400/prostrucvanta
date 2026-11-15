# PyProjects

Lightweight project and task management plugin for PyHost.

## Features

PyProjects provides lightweight project management with parent projects, subprojects, tasks, and an interactive Kanban board.

- Parent projects with a status, color, start date, target date, and owner
- Subprojects for each parent project, with their own status and color
- Tasks with a title, description, status, priority, due date, assignee, and sort position
- Project selection by name when creating tasks
- Kanban board with drag and drop, filters for project, subproject, priority, assignee, and search
- Dashboard metrics: active projects, subprojects, open tasks, overdue tasks, and recently updated tasks
- Session-based Google OAuth sign-in
- User management with `Global Administration` and `Project Access` permissions, including protection against removing the last administrator
- SQLite persistence with versioned migrations
- PyHost plugin integration at `/pyprojects`, with reverse-proxy support

## Architecture

- **FastAPI** for HTTP routes and the plugin factory
- **Jinja2** templates with Tailwind CSS and vanilla JavaScript
- **SQLite** with `PRAGMA user_version` migrations
- **Authlib** for Google OAuth OpenID Connect
- **Starlette SessionMiddleware** for secure session cookies
- **SubpathMiddleware** for reverse-proxy prefixes
- Plugin contract via the `tool_host.plugins` entry point → `app.plugin:PLUGIN`

Module layout:
- `app/main.py` – app factory, routes, middleware
- `app/db.py` – database connection and migrations
- `app/auth.py` – Google sign-in and permissions
- `app/middleware.py` – Subpath handling
- `app/security.py` – CSRF Middleware
- `app/templates/` – Jinja2 views
- `src/pyprojects/app/static/input.css` – Tailwind input and custom UI components
- `src/pyprojects/app/static/app.css` – generated stylesheet bundled with the plugin

## Frontend styles

The UI uses Tailwind CSS. The pinned Tailwind CLI version is specified in `package-lock.json`. Node.js/npm are only needed for development or to regenerate the CSS:

```bash
npm ci
npm run build:css
```

The build scans the Jinja2 templates and writes the compiled stylesheet to `src/pyprojects/app/static/app.css`. This generated CSS is included in the repository and shipped with the Python package; the running server requires neither Node.js nor a CDN connection.

## Installing in PyHost

For local development, check out `py-projects` and `pyhost` into sibling directories. PyProjects is installed into PyHost's virtual environment:

```bash
uv sync --extra test
npm ci && npm run build:css
uv sync --project ../pyhost --all-packages
uv pip install --python ../pyhost/.venv/bin/python -e .
uv run --project ../pyhost pyhost --reload
```

The PyHost server is then available at `http://127.0.0.1:8000` by default, with PyProjects mounted at `/pyprojects/`. If port 8000 is already in use, you can start PyHost with a different port, for example `--port 8001`.

Dependencies are managed through `pyproject.toml`. Python 3.13+ is required. PyProjects implements the PyHost plugin contract structurally and does not require PyHost as a project dependency.

## Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Environment variables:
- `GOOGLE_CLIENT_ID` – Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` – Google OAuth Client Secret
- `PYPROJECTS_SESSION_SECRET` – Random 32-byte secret for session cookies
- `PYPROJECTS_SECURE_COOKIES` – `true`/`false` to enable HTTPS-only cookies
- `PYPROJECTS_DB` – Path to the SQLite database; defaults to `data/pyprojects.db`
- `PYPROJECTS_BASE_PATH` – Optional reverse-proxy prefix, e.g. `/tools/pyprojects`

## Google OAuth setup

1. Create an OAuth 2.0 client in the Google Cloud Console.
2. Set the authorized redirect URI to the full callback URL. Locally, without a host prefix, use `http://localhost:8000/pyprojects/auth/google/callback`. With the PyHost prefix `/pyhost`, use `http://localhost:8000/pyhost/pyprojects/auth/google/callback`.
3. Add the client ID and secret to `.env`.
4. Start the plugin and select **Sign in with Google** at `/pyprojects/login` (with the `/pyhost` host prefix: `/pyhost/pyprojects/login`).

The first sign-in creates a user and automatically grants `Global Administration`.

## Running standalone (without PyHost)

```bash
uv run uvicorn app.main:create_app --factory --reload
```

The app runs at `http://localhost:8000`. `PYPROJECTS_BASE_PATH` is only intended for a reverse-proxy prefix when running standalone. With PyHost, the host handles the shared prefix through `TOOL_HOST_BASE_PATH` or `X-Forwarded-Prefix`; do not set `PYPROJECTS_BASE_PATH` for this.

## PyHost integration

Entry Point in `pyproject.toml`:

```toml
[project.entry-points."tool_host.plugins"]
pyprojects = "app.plugin:PLUGIN"
```

The plugin is discovered automatically at `/pyprojects`; the app factory provides the FastAPI app.

## Database path

Defaults to `data/pyprojects.db`. Override the path with `PYPROJECTS_DB`. Migrations run automatically at startup through `Database.initialize()`.

## Reverse proxy example

Nginx:
```nginx
location /tools/pyprojects/ {
    proxy_pass http://pyhost/;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

When running standalone, you can also set the plugin environment variable:
```
PYPROJECTS_BASE_PATH=/tools/pyprojects
```

With PyHost, configure the shared host prefix instead (`TOOL_HOST_BASE_PATH=/tools` or the `X-Forwarded-Prefix: /tools` header provided by a trusted proxy). The host adds the plugin path `/pyprojects`.

## Testing

```bash
uv run pytest
```

Tests cover:
1. Plugin discovery
2. CRUD operations for parent projects, subprojects, and tasks
3. Task assignment and status updates
4. Kanban ordering and consistency
5. Permissions and unauthenticated access
6. Administrator permissions and protection of the last administrator
7. Database migrations
8. Invalid input
9. URL prefix handling
10. Error cases and concurrent changes

## Building the wheel

```bash
uv build
```

Creates `dist/pyprojects-0.1.0-py3-none-any.whl`.

## Release process

1. Bump the version in `pyproject.toml` and `src/pyprojects/app/version.py`.
2. Update `CHANGES.md`.
3. Run the tests: `uv run pytest`.
4. Build the package: `uv build`.
5. Publish the wheel to PyPI or an internal index.
6. Use Conventional Commits: `feat: ...`, `fix: ...`.

## License

See the repository.
