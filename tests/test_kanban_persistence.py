import sys
sys.path.insert(0, 'src/prostrucvanta')
import tempfile, os
from app.db import Database
from app.models import utcnow

def test_kanban_position_persistence():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, 'kanban.db')
        db = Database(db_path)
        db.initialize()
        conn = db.connect()
        now = utcnow()
        # user
        conn.execute("INSERT INTO users(google_sub,email,name,created_at,last_login_at) VALUES(?,?,?,?,?)",
                     ('s','e@e','U',now,now))
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # project
        conn.execute("INSERT INTO projects(name,status,color,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?)",
                     ('P','Aktiv','#000',now,now,uid))
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # tasks
        conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id,position) VALUES(?,?,?,?,?,?,?,?)",
                     ('T1',pid,'Backlog','Normal',now,now,uid,0))
        t1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO tasks(title,project_id,status,priority,created_at,updated_at,creator_id,position) VALUES(?,?,?,?,?,?,?,?)",
                     ('T2',pid,'Backlog','Normal',now,now,uid,1))
        t2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # simulate drag drop: change status and position
        conn.execute("UPDATE tasks SET status=?, position=? WHERE id=?", ('Offen',0,t2))
        conn.execute("UPDATE tasks SET status=?, position=? WHERE id=?", ('Offen',1,t1))
        rows = conn.execute("SELECT id,status,position FROM tasks ORDER BY position").fetchall()
        assert rows[0]['id']==t2 and rows[0]['status']=='Offen' and rows[0]['position']==0
        assert rows[1]['id']==t1 and rows[1]['status']=='Offen' and rows[1]['position']==1
        print('kanban persistence OK')

if __name__=='__main__':
    test_kanban_position_persistence()
