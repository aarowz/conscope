"""Daily cleanup of events whose concert date has already passed.

Deleting from `events` cascades to price_history/alerts/alert_triggers
(ON DELETE CASCADE in scripts/init_db.py), so one DELETE clears the whole
stale footprint for an event.
"""

import os
from datetime import datetime

import psycopg2
from airflow.decorators import dag, task

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "conscope"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
}


@dag(
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["conscope", "cleanup"],
)
def stale_event_cleanup():
    @task
    def delete_past_events():
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE event_date < NOW() - INTERVAL '1 day'")
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return deleted

    delete_past_events()


stale_event_cleanup()
