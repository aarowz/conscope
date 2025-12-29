#!/usr/bin/env python3
"""
Mock producer for ConScope - generates test price events.

This producer generates realistic test data for development and testing
while waiting for API approval or when testing the pipeline without API access.
It simulates price changes over time to test price drop detection.
"""

import random
import time
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from producers.base_producer import BaseProducer
from producers.config import KAFKA_BOOTSTRAP_SERVERS, POLL_INTERVAL_SECONDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockProducer(BaseProducer):
    """
    Mock producer that generates realistic test price events.
    
    Simulates ticket prices with realistic variations:
    - Different sections (Floor, Lower Level, Upper Level)
    - Price changes over time (some increase, some decrease)
    - Multiple listings per event
    - Realistic fees and total prices
    """
    
    def __init__(
        self,
        kafka_broker: str = None,
        poll_interval: int = None,
        price_variation_pct: float = 0.15  # 15% price variation
    ):
        """
        Initialize mock producer.
        
        Args:
            kafka_broker: Kafka broker address
            poll_interval: Polling interval in seconds
            price_variation_pct: Percentage of price variation (0.15 = 15%)
        """
        super().__init__(
            source_name="mock",
            api_key="mock_api_key",
            kafka_broker=kafka_broker or KAFKA_BOOTSTRAP_SERVERS,
            poll_interval=poll_interval or POLL_INTERVAL_SECONDS,
            topic_name="raw_prices"
        )
        
        self.price_variation_pct = price_variation_pct
        # Track base prices for each listing to simulate changes
        self.listing_base_prices: Dict[str, float] = {}
        self.listing_counters: Dict[str, int] = {}
        
        logger.info("Mock producer initialized (generating test data)")
    
    def _generate_section(self) -> str:
        """Generate a realistic section name."""
        section_types = [
            "Floor", "Lower Level", "Upper Level", "Club Level",
            "Balcony", "Mezzanine", "VIP", "Premium"
        ]
        section_numbers = [str(i) for i in range(101, 150)] + ["A", "B", "C", "D"]
        
        section_type = random.choice(section_types)
        if section_type in ["Floor", "VIP", "Premium"]:
            return f"{section_type} {random.choice(['1', '2', '3', 'A', 'B'])}"
        else:
            return f"{section_type} {random.choice(section_numbers)}"
    
    def _generate_row(self) -> str:
        """Generate a realistic row identifier."""
        if random.random() < 0.3:  # 30% chance of letter rows
            return random.choice(["A", "B", "C", "D", "E", "F", "G", "H"])
        else:
            return str(random.randint(1, 30))
    
    def _generate_seat(self) -> str:
        """Generate a realistic seat number."""
        if random.random() < 0.2:  # 20% chance of multiple seats
            seat1 = random.randint(1, 25)
            seat2 = seat1 + 1
            return f"{seat1}-{seat2}"
        else:
            return str(random.randint(1, 25))
    
    def _get_base_price(self, section: str, listing_key: str) -> float:
        """Get or generate base price for a listing."""
        if listing_key not in self.listing_base_prices:
            # Generate base price based on section type
            if "Floor" in section or "VIP" in section:
                base = random.uniform(300, 800)  # Premium sections
            elif "Lower Level" in section or "Club" in section:
                base = random.uniform(150, 400)  # Mid-tier sections
            else:
                base = random.uniform(50, 200)  # Upper level/balcony
            
            self.listing_base_prices[listing_key] = base
        
        return self.listing_base_prices[listing_key]
    
    def _calculate_price_change(self, listing_key: str) -> float:
        """
        Calculate price change to simulate market dynamics.
        Prices tend to decrease slightly over time (more listings drop than increase).
        """
        if listing_key not in self.listing_counters:
            self.listing_counters[listing_key] = 0
        
        self.listing_counters[listing_key] += 1
        cycle = self.listing_counters[listing_key]
        
        # Simulate price changes:
        # - 60% chance of small decrease (market saturation)
        # - 30% chance of staying same
        # - 10% chance of increase (demand spike)
        change_factor = 1.0
        
        if random.random() < 0.6:  # Price drop
            change_factor = 1.0 - random.uniform(0.02, 0.10)  # 2-10% drop
        elif random.random() < 0.3:  # Price increase
            change_factor = 1.0 + random.uniform(0.05, 0.15)  # 5-15% increase
        
        # Add some random variation
        variation = random.uniform(-self.price_variation_pct, self.price_variation_pct)
        change_factor += variation
        
        return change_factor
    
    def fetch_listings(self, event: Dict) -> List[Dict]:
        """
        Generate mock listings for an event.
        
        Args:
            event: Event dictionary with event_id, name, venue, date
            
        Returns:
            List of mock listing dictionaries
        """
        # Generate 10-25 listings per event
        num_listings = random.randint(10, 25)
        listings = []
        
        for i in range(num_listings):
            section = self._generate_section()
            row = self._generate_row()
            seat = self._generate_seat()
            
            listing_key = f"{event['event_id']}_{section}_{row}_{seat}"
            
            # Get base price and apply changes
            base_price = self._get_base_price(section, listing_key)
            change_factor = self._calculate_price_change(listing_key)
            price = round(base_price * change_factor, 2)
            
            # Ensure price doesn't go below $20
            price = max(20.0, price)
            
            # Generate fees (typically 10-20% of ticket price)
            fees = round(price * random.uniform(0.10, 0.20), 2)
            total_price = round(price + fees, 2)
            
            # Generate quantity (usually 1-2 tickets)
            quantity = random.choice([1, 1, 1, 2])  # 75% single, 25% pair
            
            listing = {
                "id": f"mock_{event['event_id']}_{i}_{int(time.time())}",
                "section": section,
                "row": row,
                "seat_number": seat,
                "price": price,
                "fees": {"total": fees},
                "total_price": total_price,
                "quantity": quantity,
                "delivery_method": random.choice(["mobile", "instant", "mobile"]),
                "url": f"https://mock-tickets.com/event/{event['event_id']}/listing/{i}"
            }
            
            listings.append(listing)
        
        return listings
    
    def parse_listing(self, listing: Dict, event: Dict) -> Dict:
        """
        Convert mock listing to PriceEvent format.
        
        Args:
            listing: Mock listing dictionary
            event: Event dictionary with event_id, name, venue, date
            
        Returns:
            Dictionary in PriceEvent format
        """
        # Parse event date
        event_date = event.get('date')
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            except:
                event_date = datetime.now() + timedelta(days=30)
        elif not isinstance(event_date, datetime):
            event_date = datetime.now() + timedelta(days=30)
        
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
        delivery_method = listing.get('delivery_method', 'mobile')
        
        # Create PriceEvent dictionary
        price_event = {
            "event_id": event.get('event_id', ''),
            "event_name": event.get('name', ''),
            "venue": event.get('venue', ''),
            "event_date": event_date.isoformat() if isinstance(event_date, datetime) else event_date,
            "source": "mock",
            "section": section,
            "row": str(row),
            "seat": str(seat_number),
            "price": price,
            "fees": fees if fees > 0 else None,
            "total_price": total_price,
            "timestamp": datetime.now().isoformat(),
            "listing_id": f"mock_{listing_id}",
            "listing_url": listing_url,
            "quantity": quantity,
            "delivery_method": delivery_method,
            "seller_notes": None
        }
        
        return price_event


def main():
    """Main entry point for mock producer."""
    import sys
    from producers.test_events import TEST_EVENTS
    
    # Use test events from test_events.py
    test_events = TEST_EVENTS
    
    # Initialize producer
    producer = MockProducer(poll_interval=30)  # Poll every 30 seconds for testing
    
    logger.info("Starting mock producer (generating test data)")
    logger.info(f"Tracking {len(test_events)} test events")
    logger.info("Press Ctrl+C to stop")
    
    # Run producer
    try:
        producer.run(test_events)
    except KeyboardInterrupt:
        logger.info("Mock producer stopped by user")
    except Exception as e:
        logger.error(f"Mock producer error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

