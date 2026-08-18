import sqlite3, json
db = r"C:\Users\downl\.hermes\ebbinghaus_memory.db"
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
cur = con.cursor()

r = cur.execute("SELECT * FROM memories WHERE memory_id=46837").fetchone()
print(json.dumps(dict(r), ensure_ascii=False, default=str))
