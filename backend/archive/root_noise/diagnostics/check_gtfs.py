import sqlite3
conn = sqlite3.connect('cache/transit.db')
cursor = conn.cursor()

# route_stops tablosunu kontrol et
cursor.execute("PRAGMA table_info(route_stops)")
print('route_stops columns:', cursor.fetchall())

# Ornek route_stops
cursor.execute("SELECT * FROM route_stops WHERE route_code='319' LIMIT 10")
for r in cursor.fetchall():
    print('route_stop:', r)

# stops tablosunu kontrol et
cursor.execute("PRAGMA table_info(stops)")
print('stops columns:', cursor.fetchall())

# Ornek stop
cursor.execute("SELECT * FROM stops LIMIT 1")
for s in cursor.fetchall():
    print('stop:', s)

conn.close()
print('Done')