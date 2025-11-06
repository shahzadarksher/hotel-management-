import sqlite3
import os
from flask import g, current_app


def connect_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE', os.path.join(os.path.dirname(__file__), 'hotel.db'))
        g.db = connect_db(db_path)
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    db_path = app.config['DATABASE']
    conn = connect_db(db_path)
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT UNIQUE,
        type TEXT,
        price REAL,
        available INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        room_id INTEGER,
        checkin TEXT,
        checkout TEXT,
        -- status: booked, checked-in, checked-out, cancelled
        status TEXT DEFAULT 'booked',
        FOREIGN KEY(room_id) REFERENCES rooms(id)
    );
    ''')
    # ensure bookings table has a status column (for migrations on existing DBs)
    try:
        c.execute("PRAGMA table_info(bookings)")
        cols = [r[1] for r in c.fetchall()]
        if 'status' not in cols:
            c.execute("ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'booked'")
    except Exception:
        # ignore if table doesn't exist yet or PRAGMA fails
        pass

    # seed with a few rooms if empty
    c.execute('SELECT COUNT(*) FROM rooms')
    if c.fetchone()[0] == 0:
        rooms = [
            ('101', 'Single', 50.0, 1),
            ('102', 'Double', 80.0, 1),
            ('201', 'Suite', 150.0, 1),
        ]
        c.executemany('INSERT INTO rooms (number, type, price, available) VALUES (?, ?, ?, ?)', rooms)
    conn.commit()
    conn.close()
