import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "crm.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'processed',
            amount REAL DEFAULT 0,
            executor TEXT DEFAULT 'Не назначен',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('text','number','date','choice'))
        )
        """
    )
    # add required column if absent
    try:
        cur.execute("ALTER TABLE custom_fields ADD COLUMN required INTEGER DEFAULT 0")
    except Exception:
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_fields (
            ticket_id INTEGER NOT NULL,
            field_id INTEGER NOT NULL,
            value TEXT,
            PRIMARY KEY (ticket_id, field_id),
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
            FOREIGN KEY(field_id) REFERENCES custom_fields(id) ON DELETE CASCADE
        )
        """
    )

    # Executors for assignment
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS executors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            daily_limit INTEGER DEFAULT 10,
            assigned_today INTEGER DEFAULT 0,
            parameters TEXT DEFAULT ''
        )
        """
    )
    try:
        cur.execute("ALTER TABLE executors ADD COLUMN active INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE executors ADD COLUMN last_ping TIMESTAMP")
    except Exception:
        pass

    # Rule sets (simple JSON)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rule_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rules TEXT DEFAULT '{}',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Licenses and settings
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL,
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activated_by INTEGER,
            activated_at TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK(id=1),
            active_plan TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # ensure a single settings row
    cur.execute("INSERT OR IGNORE INTO settings (id, active_plan) VALUES (1, NULL)")
    # Add hidden_base_fields if missing
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN hidden_base_fields TEXT DEFAULT '[]'")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN ddos_block_until INTEGER")
    except Exception:
        pass

    # Service status
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS service_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL, -- heartbeat|error
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
