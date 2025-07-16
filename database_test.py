import sqlite3

def init_db():
    conn = sqlite3.connect('budget_app.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
            email TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            month TEXT,
            budget REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            category TEXT,
            amount REAL,
            date TEXT,
            note TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            target_amount REAL,
            saved_amount REAL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS spending_limits (
            user_id INTEGER,
            month TEXT,
            category TEXT,
            limit_amount REAL,
            PRIMARY KEY (user_id, month, category)
        )
    ''')

    c.execute('''CREATE TABLE IF NOT EXISTS savings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        month TEXT,
        year TEXT,
        amount REAL,
        source TEXT CHECK(source IN ('remaining', 'manual'))
    )''')

    conn.commit()
    conn.close()
