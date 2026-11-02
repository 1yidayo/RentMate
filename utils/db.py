import sqlite3
import json
from datetime import datetime

DB_PATH = "rentmate.db"

def init_db():
    """Initialize the SQLite database and create tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            rent INTEGER,
            size_ping REAL,
            location TEXT,
            district TEXT,
            floor TEXT,
            building_type TEXT,
            bedrooms INTEGER,
            bathrooms INTEGER,
            has_ac INTEGER DEFAULT 0,
            has_washing_machine INTEGER DEFAULT 0,
            has_fridge INTEGER DEFAULT 0,
            has_internet INTEGER DEFAULT 0,
            has_parking INTEGER DEFAULT 0,
            pet_friendly INTEGER DEFAULT 0,
            gender_restriction TEXT,
            deposit TEXT,
            utilities TEXT,
            near_mrt TEXT,
            near_school TEXT,
            contact TEXT,
            notes TEXT,
            raw_text TEXT,
            source_url TEXT,
            confidence TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_listing(data: dict) -> int:
    """Insert a new listing and return its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO listings (
            title, rent, size_ping, location, district, floor,
            building_type, bedrooms, bathrooms,
            has_ac, has_washing_machine, has_fridge, has_internet, has_parking,
            pet_friendly, gender_restriction, deposit, utilities,
            near_mrt, near_school, contact, notes,
            raw_text, source_url, confidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title", "未命名物件"),
        data.get("rent"),
        data.get("size_ping"),
        data.get("location"),
        data.get("district"),
        data.get("floor"),
        data.get("building_type"),
        data.get("bedrooms"),
        data.get("bathrooms"),
        int(data.get("has_ac", False)),
        int(data.get("has_washing_machine", False)),
        int(data.get("has_fridge", False)),
        int(data.get("has_internet", False)),
        int(data.get("has_parking", False)),
        int(data.get("pet_friendly", False)),
        data.get("gender_restriction"),
        data.get("deposit"),
        data.get("utilities"),
        data.get("near_mrt"),
        data.get("near_school"),
        data.get("contact"),
        data.get("notes"),
        data.get("raw_text", ""),
        data.get("source_url", ""),
        json.dumps(data.get("confidence", {}), ensure_ascii=False),
        now,
    ))
    listing_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return listing_id

def get_all_listings() -> list[dict]:
    """Return all listings as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings ORDER BY created_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def delete_listing(listing_id: int):
    """Delete a listing by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()

def get_listing_by_id(listing_id: int) -> dict | None:
    """Return a single listing by ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
