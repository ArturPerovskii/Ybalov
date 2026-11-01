
import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).with_name("weather.db")


def connect():
    return sqlite3.connect(DB_NAME)


def initialize():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL UNIQUE,
                pressure REAL NOT NULL,
                temperature REAL NOT NULL
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_timestamp
            ON weather(timestamp)
        """)


def save_weather(timestamp, pressure, temperature):
    with connect() as db:
        db.execute("""
            INSERT INTO weather (timestamp, pressure, temperature)
            VALUES (?, ?, ?)
            ON CONFLICT(timestamp) DO UPDATE SET
                pressure = excluded.pressure,
                temperature = excluded.temperature
        """, (timestamp, pressure, temperature))


def save_weather_batch(records):
    """
    Сохраняет список измерений из облачной базы.
    Существующие записи обновляются, дубликаты не создаются.
    """

    values = [
        (
            item["timestamp"],
            item["pressure"],
            item["temperature"]
        )
        for item in records
    ]

    if not values:
        return

    with connect() as db:
        db.executemany("""
            INSERT INTO weather (
                timestamp,
                pressure,
                temperature
            )
            VALUES (?, ?, ?)
            ON CONFLICT(timestamp) DO UPDATE SET
                pressure = excluded.pressure,
                temperature = excluded.temperature
        """, values)


def get_history():
    with connect() as db:
        return db.execute("""
            SELECT timestamp, pressure, temperature
            FROM weather
            ORDER BY timestamp
        """).fetchall()


def clear_history():
    with connect() as db:
        db.execute("DELETE FROM weather")
