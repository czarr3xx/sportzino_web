import sqlite3

conn = sqlite3.connect('referral_link.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL
    )
''')
conn.commit()
conn.close()
