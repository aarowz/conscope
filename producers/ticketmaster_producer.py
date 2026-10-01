#!/usr/bin/env python3
"""
Ticketmaster API producer for ConScope.

This producer polls the Ticketmaster Discovery API for event price ranges
and publishes price events to Kafka. Unlike SeatGeek, Ticketmaster's public
API exposes aggregate price ranges per event (not individual seat listings),
so each price range (e.g. "standard", "VIP") is published as one listing.
"""

import requests
import logging
from typing import List, Dict
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from producers.base_producer import BaseProducer
from producers.config import (
    TICKETMASTER_API_KEY,
    TICKETMASTER_BASE_URL,
    KAFKA_BOOTSTRAP_SERVERS,
    POLL_INTERVAL_SECONDS,
    TICKETMASTER_SEED_KEYWORD,
    TICKETMASTER_MAX_TRACKED_EVENTS
)
from producers.ticketmaster_discovery import discover_events
from producers.events_store import get_tracked_events, upsert_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TicketmasterProducer(BaseProducer):
    """
    Producer for Ticketmaster event price ranges.

    Polls the Discovery API every N seconds and publishes one price event
    per price range (type) returned for each tracked event.
    """

    def __init__(
        self,
        api_key: str = None,
        kafka_broker: str = None,
        poll_interval: int = None
    ):
        api_key = api_key or TICKETMASTER_API_KEY
        if not api_key:
            raise ValueError(
                "Ticketmaster API key required. Set TICKETMASTER_API_KEY in .env or pass as argument."
            )

        super().__init__(
            source_name="ticketmaster",
            api_key=api_key,
            kafka_broker=kafka_broker or KAFKA_BOOTSTRAP_SERVERS,
            poll_interval=poll_interval or POLL_INTERVAL_SECONDS,
            topic_name="raw_prices"
        )

        self.base_url = TICKETMASTER_BASE_URL

    def fetch_listings(self, event: Dict) -> List[Dict]:
        """
        Fetch price ranges for a specific event from the Ticketmaster Discovery API.

        Args:
            event: Event dictionary with event_id (Ticketmaster event ID), name, venue, date

        Returns:
            List of priceRange dictionaries, e.g. [{"type": "standard", "currency": "USD", "min": 45.0, "max": 120.0}]
        """
        event_id = event.get('event_id')
        if not event_id:
            logger.error("Event missing event_id")
            return []

        try:
            url = f"{self.base_url}/events/{event_id}.json"
            params = {"apikey": self.api_key}

            logger.debug(f"Fetching price ranges from Ticketmaster for event {event_id}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            price_ranges = data.get('priceRanges', [])

            logger.info(
                f"Fetched {len(price_ranges)} price range(s) from Ticketmaster for event {event_id}"
            )

            return price_ranges

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching Ticketmaster data for event {event_id}")
            return []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Event {event_id} not found on Ticketmaster")
            elif e.response.status_code == 429:
                logger.warning("Ticketmaster rate limit exceeded. Waiting...")
            else:
                logger.error(f"HTTP error fetching Ticketmaster data: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Ticketmaster data for event {event_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching Ticketmaster price ranges: {e}")
            return []

    def parse_listing(self, listing: Dict, event: Dict) -> Dict:
        """
        Convert a Ticketmaster priceRange entry to PriceEvent format.

        Args:
            listing: A single priceRange dict from the Discovery API
            event: Event dictionary with event_id, name, venue, date

        Returns:
            Dictionary in PriceEvent format
        """
        price_type = listing.get('type', 'standard')
        min_price = float(listing.get('min', 0))
        max_price = float(listing.get('max', min_price))

        event_date = event.get('date')
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            except ValueError:
                event_date = datetime.now()

        price_event = {
            "event_id": event.get('event_id', ''),
            "event_name": event.get('name', ''),
            "venue": event.get('venue', ''),
            "event_date": event_date.isoformat() if isinstance(event_date, datetime) else event_date,
            "source": "ticketmaster",
            "section": price_type.title(),
            "row": "N/A",
            "seat": "N/A",
            "price": min_price,
            "fees": None,
            "total_price": max_price,
            "timestamp": datetime.now().isoformat(),
            "listing_id": f"ticketmaster_{event.get('event_id', '')}_{price_type}",
            "listing_url": event.get('url', ''),
            "quantity": 1,
            "delivery_method": None,
            "seller_notes": None
        }

        return price_event


def main():
    """Main entry point for Ticketmaster producer."""

    if not TICKETMASTER_API_KEY:
        logger.error(
            "TICKETMASTER_API_KEY not found. Please set it in your .env file or environment."
        )
        logger.info("Get your API key from: https://developer.ticketmaster.com/")
        sys.exit(1)

    producer = TicketmasterProducer()

    if not get_tracked_events(limit=1):
        logger.info(f"No tracked events yet. Seeding via keyword search: '{TICKETMASTER_SEED_KEYWORD}'")
        for event in discover_events(TICKETMASTER_SEED_KEYWORD, TICKETMASTER_API_KEY, TICKETMASTER_BASE_URL):
            upsert_event(event)

    try:
        producer.run(lambda: get_tracked_events(limit=TICKETMASTER_MAX_TRACKED_EVENTS))
    except KeyboardInterrupt:
        logger.info("Producer stopped by user")
    except Exception as e:
        logger.error(f"Producer error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
