"""
Shared `events` table access for discovery.

Used by the Ticketmaster producer (to decide what to poll) and the dashboard
(to persist events found through a live search) so neither has to hardcode
event IDs.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List

import psycopg2

logger = logging.getLogger(__name__)


def _db_config():
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DB", "conscope"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "password"),
    }


def get_tracked_events(limit: int = 25) -> List[Dict]:
    """Events currently tracked in Postgres, soonest first."""
    try:
        conn = psycopg2.connect(**_db_config())
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT event_id, event_name, venue, event_date
            FROM events
            ORDER BY event_date ASC
            LIMIT %s
            """,
            [limit],
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {"event_id": r[0], "name": r[1], "venue": r[2], "date": r[3].isoformat()}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Error loading tracked events: {e}")
        return []


def upsert_event(event: Dict) -> bool:
    """Insert a discovered event, filling in city/state if they were missing."""
    event_id = event.get("event_id")
    if not event_id:
        return False

    date_value = event.get("date")
    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            date_value = datetime.now()
    elif not isinstance(date_value, datetime):
        date_value = datetime.now()

    try:
        conn = psycopg2.connect(**_db_config())
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (event_id, event_name, venue, event_date, city, state)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO UPDATE
            SET city = COALESCE(events.city, EXCLUDED.city),
                state = COALESCE(events.state, EXCLUDED.state),
                last_updated = NOW()
            """,
            (
                event_id,
                event.get("name", ""),
                event.get("venue", ""),
                date_value,
                event.get("city"),
                event.get("state"),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error upserting event {event_id}: {e}")
        return False
