import sqlite3
from pathlib import Path

SCHEMA_V1 = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  google_sub TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL,
  name TEXT NOT NULL DEFAULT '',
  picture_url TEXT,
  created_at TEXT NOT NULL,
  last_login_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_permissions (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  permission TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  PRIMARY KEY(user_id, permission)
);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK(status IN ('Aktiv','Pausiert','Abgeschlossen','Archiviert')),
  color TEXT NOT NULL DEFAULT '#3b82f6',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  start_date TEXT,
  target_date TEXT,
  owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE TABLE IF NOT EXISTS subprojects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK(status IN ('Aktiv','Pausiert','Abgeschlossen','Archiviert')),
  color TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  start_date TEXT,
  target_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_subprojects_project ON subprojects(project_id);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  subproject_id INTEGER REFERENCES subprojects(id) ON DELETE SET NULL,
  status TEXT NOT NULL CHECK(status IN ('Backlog','Offen','In Bearbeitung','Blockiert','Erledigt')),
  priority TEXT NOT NULL CHECK(priority IN ('Niedrig','Normal','Hoch','Kritisch')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  due_date TEXT,
  start_date TEXT,
  assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
  position INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_subproject ON tasks(subproject_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""

class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        conn = self.connect()
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    conn.executescript(SCHEMA_V1)
                    conn.execute("PRAGMA user_version = 1")
                    version = 1
                # Versioned migrations
                if version < 2:
                    # v002 add indexes
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id)")
                    conn.execute("PRAGMA user_version = 2")
                if conn.execute("PRAGMA foreign_key_check").fetchall():
                    raise RuntimeError("Foreign key check failed")
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.close()
