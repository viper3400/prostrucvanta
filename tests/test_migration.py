import sys
sys.path.insert(0, 'src/pyprojects')
import tempfile, os
from app.db import Database

def test_migration_version():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, 'mig.db')
        db = Database(db_path)
        db.initialize()
        conn = db.connect()
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver >= 1
        # ensure tables exist
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in ['users','projects','subprojects','tasks']:
            assert t in tables
        print('migration OK')

if __name__ == '__main__':
    test_migration_version()
