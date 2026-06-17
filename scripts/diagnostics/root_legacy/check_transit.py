import sqlite3

db = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner\backend\cache\transit.db'
try:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # Check tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print('Tables:', [t[0] for t in tables])
    
    # Check counts
    for t in tables:
        name = t[0]
        cur.execute(f'SELECT COUNT(*) FROM {name}')
        cnt = cur.fetchone()[0]
        print(f'{name}: {cnt:,} rows')
    
    # Check metro data
    cur.execute("SELECT name FROM metro_lines LIMIT 10")
    print('\nMetro Lines:')
    for row in cur.fetchall():
        print(f'  {row[0]}')
    
    conn.close()
except Exception as e:
    print(f'Error: {e}')
