import sys
sys.path.insert(0, 'src/pyprojects')
import tempfile, os
from app.db import Database
from app.auth import AuthService
from app.models import utcnow

def test_last_admin_protection():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, 'perm.db')
        db = Database(db_path)
        db.initialize()
        auth = AuthService(db)
        now = utcnow()
        conn = db.connect()
        conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                     ('sub1','a@b.c','A',now,now))
        uid1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                     ('sub2','b@c.d','B',now,now))
        uid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO user_permissions(user_id,permission,granted_at) VALUES(?,?,?)",
                     (uid1,'Global Administration',now))
        conn.commit()
        # try remove last admin -> should raise
        try:
            auth.set_permission(uid1, 'Global Administration', False)
            raise AssertionError('Should have raised')
        except ValueError as e:
            assert 'letzte globale Administration' in str(e)
        print('last admin protection OK')

if __name__ == '__main__':
    test_last_admin_protection()
