import sys
sys.path.insert(0, 'src/prostrucvanta')
import tempfile, os
from app.db import Database
from app.auth import AuthService
from app.models import utcnow

def test_full_flow():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, 'full.db')
        db = Database(db_path)
        db.initialize()
        auth = AuthService(db)
        now = utcnow()
        conn = db.connect()
        # create users
        conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                     ('u1','a@b','A',now,now))
        uid1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                     ('u2','b@c','B',now,now))
        uid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # permissions
        conn.execute("INSERT INTO user_permissions(user_id,permission,granted_at) VALUES(?,?,?)",
                     (uid1,'Global Administration',now))
        conn.execute("INSERT INTO user_permissions(user_id,permission,granted_at) VALUES(?,?,?)",
                     (uid2,'Project Access',now))
        # project
        conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                     ('P1','Aktiv','#111',now,now,uid1))
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # subproject
        conn.execute("INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                     (pid,'S1','Aktiv',now,now))
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # tasks
        conn.execute("INSERT INTO tasks(title,project_id,subproject_id,status,priority,created_at,updated_at,creator_id,assignee_id,position) VALUES(?,?,?,?,?,?,?,?,?,?)",
                     ('T1',pid,sid,'Backlog','Hoch',now,now,uid1,uid2,0))
        t1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # duplicate
        conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id,position) VALUES(?,?,?,?,?,?,?,?)",
                     ('T1 Kopie',pid,'Backlog','Hoch',now,now,uid1,0))
        # update status and position
        conn.execute("UPDATE tasks SET status='Offen', position=1 WHERE id=?", (t1,))
        # archive project
        conn.execute("UPDATE projects SET status='Archiviert', updated_at=? WHERE id=?", (now,pid))
        # verify
        p = conn.execute("SELECT status FROM projects WHERE id=?", (pid,)).fetchone()
        assert p['status']=='Archiviert'
        tasks = conn.execute("SELECT title,status FROM tasks WHERE project_id=?", (pid,)).fetchall()
        titles = [t['title'] for t in tasks]
        assert 'T1 Kopie' in titles
        print('integration flow OK')

if __name__=='__main__':
    test_full_flow()
