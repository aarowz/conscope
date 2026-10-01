"""
Ticketmaster Discovery API event search.

Pure HTTP helper (no Kafka) so both the producer and the dashboard can
discover events by keyword instead of relying on a hardcoded event list.
"""

import logging
from datetime import datetime
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def discover_events(keyword: str, api_key: str, base_url: str, size: int = 20) -> List[Dict]:
    """
    Search Ticketmaster's Discovery API for events matching a keyword.

    Returns a list of dicts: event_id, name, venue, date, city, state, url.
    """
    if not keyword or not api_key:
        return []

    try:
        response = requests.get(
            f"{base_url}/events.json",
            params={
                "apikey": api_key,
                "keyword": keyword,
                "size": size,
                "sort": "relevance,desc",
            },
            timeout=10,
        )
        response.raise_for_status()
        raw_events = response.json().get("_embedded", {}).get("events", [])
    except requests.exceptions.Timeout:
        logger.error(f"Timeout searching Ticketmaster for '{keyword}'")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            logger.warning("Ticketmaster rate limit exceeded during search")
        else:
            logger.error(f"HTTP error searching Ticketmaster for '{keyword}': {e}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching Ticketmaster for '{keyword}': {e}")
        return []

    events = []
    for raw in raw_events:
        event_id = raw.get("id")
        if not event_id:
            continue
        venue = (raw.get("_embedded", {}).get("venues") or [{}])[0]
        events.append({
            "event_id": event_id,
            "name": raw.get("name", ""),
            "venue": venue.get("name", ""),
            "city": (venue.get("city") or {}).get("name"),
            "state": (venue.get("state") or {}).get("stateCode"),
            "date": raw.get("dates", {}).get("start", {}).get("dateTime") or datetime.now().isoformat(),
            "url": raw.get("url", ""),
        })
    return events
