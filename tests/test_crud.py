import sys
sys.path.insert(0, 'src/prostrucvanta')
import tempfile, os
from app.db import Database
from app.models import utcnow

def test_db_init_and_crud():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, 'test.db')
        db = Database(db_path)
        db.initialize()
        conn = db.connect()
        # create user
        now = utcnow()
        conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                     ('sub1','a@b.c','Alice',now,now))
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # project
        conn.execute("INSERT INTO projects(name,description,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?,?)",
                     ('P1','', 'Aktiv','#111',now,now,user_id))
        proj_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # subproject
        conn.execute("INSERT INTO subprojects(project_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                     (proj_id,'S1','Aktiv',now,now))
        # task
        conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id) VALUES(?,?,?,?,?,?,?)",
                     ('T1',proj_id,'Backlog','Normal',now,now,user_id))
        # verify
        p = conn.execute("SELECT * FROM projects WHERE id=?", (proj_id,)).fetchone()
        assert p['name'] == 'P1'
        print('DB CRUD OK')

if __name__ == '__main__':
    test_db_init_and_crud()
