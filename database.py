import sqlite3

DB_NAME = "weather.db"


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