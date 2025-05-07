import sqlite3

# Connect to the database (creates it if it doesn't exist)
conn = sqlite3.connect('kyc_database.db')
cursor = conn.cursor()

# Create the table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS kyc_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        country TEXT NOT NULL,
        wallet_address TEXT NOT NULL,
        id_file TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
''')

conn.commit()
conn.close()

print("Database and table created successfully.")
