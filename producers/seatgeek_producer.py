#!/usr/bin/env python3
"""
SeatGeek API producer for ConScope.

This producer polls the SeatGeek API for ticket listings and publishes
price events to Kafka. It handles rate limiting, error recovery, and
converts SeatGeek's API format to our standard PriceEvent format.
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
    SEATGEEK_API_KEY,
    SEATGEEK_BASE_URL,
    KAFKA_BOOTSTRAP_SERVERS,
    POLL_INTERVAL_SECONDS,
    DEFAULT_EVENTS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeatGeekProducer(BaseProducer):
    """
    Producer for SeatGeek ticket prices.
    
    Polls SeatGeek API every N seconds and publishes price events to Kafka.
    """
    
    def __init__(
        self,
        api_key: str = None,
        kafka_broker: str = None,
        poll_interval: int = None
    ):
        """
        Initialize SeatGeek producer.
        
        Args:
            api_key: SeatGeek API key (client_id). If None, uses SEATGEEK_API_KEY from config.
            kafka_broker: Kafka broker address. If None, uses KAFKA_BOOTSTRAP_SERVERS from config.
            poll_interval: Polling interval in seconds. If None, uses POLL_INTERVAL_SECONDS from config.
        """
        api_key = api_key or SEATGEEK_API_KEY
        if not api_key:
            raise ValueError(
                "SeatGeek API key required. Set SEATGEEK_API_KEY in .env or pass as argument."
            )
        
        super().__init__(
            source_name="seatgeek",
            api_key=api_key,
            kafka_broker=kafka_broker or KAFKA_BOOTSTRAP_SERVERS,
            poll_interval=poll_interval or POLL_INTERVAL_SECONDS,
            topic_name="raw_prices"
        )
        
        self.base_url = SEATGEEK_BASE_URL
    
    def fetch_listings(self, event: Dict) -> List[Dict]:
        """
        Fetch listings for a specific event from SeatGeek API.
        
        Args:
            event: Event dictionary with event_id (SeatGeek event ID), name, venue, date
            
        Returns:
            List of listing dictionaries from SeatGeek API
        """
        event_id = event.get('event_id')
        if not event_id:
            logger.error("Event missing event_id")
            return []
        
        try:
            url = f"{self.base_url}/events/{event_id}/listings"
            params = {
                "client_id": self.api_key,
                "per_page": 100,  # Get up to 100 listings per request
                "sort": "price",  # Sort by price (ascending)
                "order": "asc"
            }
            
            logger.debug(f"Fetching listings from SeatGeek for event {event_id}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            listings = data.get('listings', [])
            
            logger.info(
                f"Fetched {len(listings)} listings from SeatGeek for event {event_id}"
            )
            
            return listings
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching SeatGeek data for event {event_id}")
            return []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Event {event_id} not found on SeatGeek")
            elif e.response.status_code == 429:
                logger.warning("SeatGeek rate limit exceeded. Waiting...")
                # Could implement exponential backoff here
            else:
                logger.error(f"HTTP error fetching SeatGeek data: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching SeatGeek data for event {event_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching SeatGeek listings: {e}")
            return []
    
    def parse_listing(self, listing: Dict, event: Dict) -> Dict:
        """
        Convert SeatGeek listing to PriceEvent format.
        
        Args:
            listing: Raw listing dictionary from SeatGeek API
            event: Event dictionary with event_id, name, venue, date
            
        Returns:
            Dictionary in PriceEvent format
        """
        # Extract price information
        price = float(listing.get('price', 0))
        fees_dict = listing.get('fees', {})
        fees = float(fees_dict.get('total', 0)) if fees_dict else 0.0
        total_price = float(listing.get('total_price', price + fees))
        
        # Extract seat information
        section = listing.get('section', 'Unknown')
        row = listing.get('row', 'Unknown')
        seat_number = listing.get('seat_number', 'Unknown')
        
        # Extract listing metadata
        listing_id = str(listing.get('id', ''))
        listing_url = listing.get('url', '')
        quantity = int(listing.get('quantity', 1))
        delivery_method = listing.get('delivery_method', 'unknown')
        
        # Parse event date
        event_date = event.get('date')
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            except:
                event_date = datetime.now()
        
        # Create PriceEvent dictionary
        price_event = {
            "event_id": event.get('event_id', ''),
            "event_name": event.get('name', ''),
            "venue": event.get('venue', ''),
            "event_date": event_date.isoformat() if isinstance(event_date, datetime) else event_date,
            "source": "seatgeek",
            "section": section,
            "row": str(row),
            "seat": str(seat_number),
            "price": price,
            "fees": fees if fees > 0 else None,
            "total_price": total_price,
            "timestamp": datetime.now().isoformat(),
            "listing_id": f"seatgeek_{listing_id}",
            "listing_url": listing_url,
            "quantity": quantity,
            "delivery_method": delivery_method,
            "seller_notes": None
        }
        
        return price_event


def main():
    """Main entry point for SeatGeek producer."""
    
    # Check for API key
    if not SEATGEEK_API_KEY:
        logger.error(
            "SEATGEEK_API_KEY not found. Please set it in your .env file or environment."
        )
        logger.info("Get your API key from: https://platform.seatgeek.com/")
        sys.exit(1)
    
    # Initialize producer
    producer = SeatGeekProducer()
    
    # Events to track
    # You can override DEFAULT_EVENTS in config.py or pass events here
    events = DEFAULT_EVENTS
    
    if not events:
        logger.warning("No events configured. Add events to producers/config.py DEFAULT_EVENTS")
        logger.info("Example event format:")
        logger.info('{"event_id": "6174046", "name": "Taylor Swift", "venue": "MetLife", "date": "2025-05-15T19:00:00Z"}')
        sys.exit(1)
    
    # Run producer
    try:
        producer.run(events)
    except KeyboardInterrupt:
        logger.info("Producer stopped by user")
    except Exception as e:
        logger.error(f"Producer error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

