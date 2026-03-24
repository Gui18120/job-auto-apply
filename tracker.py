import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tracker.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id      TEXT UNIQUE,
            job_title   TEXT,
            company     TEXT,
            platform    TEXT,
            url         TEXT,
            location    TEXT,
            mode        TEXT,
            status      TEXT DEFAULT 'applied',
            applied_at  TEXT,
            notes       TEXT
        )
    """)
    conn.commit()
    conn.close()


def already_applied(job_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM applications WHERE job_id = ?", (job_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def save_application(job_id, job_title, company, platform, url,
                     location="", mode="", status="applied", notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO applications
                (job_id, job_title, company, platform, url, location, mode, status, applied_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, job_title, company, platform, url,
              location, mode, status, datetime.now().isoformat(), notes))
        conn.commit()
        print(f"[Tracker] Salvo: {job_title} @ {company} ({platform})")
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def list_applications(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT job_title, company, platform, location, mode, status, applied_at
        FROM applications
        ORDER BY applied_at DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def print_report():
    rows = list_applications()
    print(f"\n{'='*60}")
    print(f"  CANDIDATURAS ENVIADAS ({len(rows)})")
    print(f"{'='*60}")
    for r in rows:
        title, company, platform, location, mode, status, applied_at = r
        date = applied_at[:10] if applied_at else "?"
        print(f"  [{date}] {title} @ {company} | {platform} | {mode} | {status}")
    print(f"{'='*60}\n")
