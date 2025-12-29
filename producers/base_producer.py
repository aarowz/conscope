"""
Base producer class for ConScope ticket price producers.

This abstract base class provides common functionality for all ticket source producers,
including Kafka connection, error handling, and metrics tracking.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseProducer(ABC):
    """
    Abstract base class for ticket price producers.
    
    All producers (SeatGeek, Ticketmaster, etc.) should inherit from this class
    and implement the fetch_listings() and parse_listing() methods.
    """
    
    def __init__(
        self,
        source_name: str,
        api_key: str,
        kafka_broker: str = 'localhost:9092',
        poll_interval: int = 60,
        topic_name: str = 'raw_prices'
    ):
        """
        Initialize base producer.
        
        Args:
            source_name: Name of the ticket source (e.g., "seatgeek")
            api_key: API key for the ticket source
            kafka_broker: Kafka broker address
            poll_interval: Polling interval in seconds
            topic_name: Kafka topic to publish to
        """
        self.source_name = source_name
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.topic_name = topic_name
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            max_in_flight_requests_per_connection=1,  # Ensure ordering
            compression_type='snappy',
            batch_size=16384,  # 16KB batches
            linger_ms=10  # Wait up to 10ms for batching
        )
        
        # Metrics tracking
        self.metrics = {
            'total_events_sent': 0,
            'total_api_calls': 0,
            'total_errors': 0,
            'last_poll_time': None,
            'avg_api_latency_ms': 0
        }
        
        logger.info(f"Initialized {source_name} producer (poll_interval={poll_interval}s)")
    
    @abstractmethod
    def fetch_listings(self, event: Dict) -> List[Dict]:
        """
        Fetch listings for a specific event from the API.
        
        Args:
            event: Event dictionary with event_id, name, venue, date
            
        Returns:
            List of raw listing dictionaries from the API
        """
        pass
    
    @abstractmethod
    def parse_listing(self, listing: Dict, event: Dict) -> Dict:
        """
        Parse a raw listing from the API into PriceEvent format.
        
        Args:
            listing: Raw listing dictionary from API
            event: Event dictionary with event_id, name, venue, date
            
        Returns:
            Dictionary in PriceEvent format (will be converted to PriceEvent)
        """
        pass
    
    def send_price_event(self, price_event_dict: Dict) -> bool:
        """
        Send a price event to Kafka.
        
        Args:
            price_event_dict: PriceEvent as dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            future = self.producer.send(self.topic_name, value=price_event_dict)
            # Wait for the message to be sent (with timeout)
            record_metadata = future.get(timeout=10)
            
            self.metrics['total_events_sent'] += 1
            logger.debug(
                f"Sent price event: {price_event_dict.get('section')} "
                f"Row {price_event_dict.get('row')} - ${price_event_dict.get('price')}"
            )
            return True
            
        except KafkaError as e:
            self.metrics['total_errors'] += 1
            logger.error(f"Error sending message to Kafka: {e}")
            return False
        except Exception as e:
            self.metrics['total_errors'] += 1
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    def process_event(self, event: Dict) -> int:
        """
        Process a single event: fetch listings and send to Kafka.
        
        Args:
            event: Event dictionary with event_id, name, venue, date
            
        Returns:
            Number of listings processed
        """
        start_time = time.time()
        
        try:
            # Fetch listings from API
            listings = self.fetch_listings(event)
            self.metrics['total_api_calls'] += 1
            
            # Calculate API latency
            api_latency = (time.time() - start_time) * 1000
            # Update rolling average
            if self.metrics['avg_api_latency_ms'] == 0:
                self.metrics['avg_api_latency_ms'] = api_latency
            else:
                self.metrics['avg_api_latency_ms'] = (
                    self.metrics['avg_api_latency_ms'] * 0.9 + api_latency * 0.1
                )
            
            if not listings:
                logger.warning(f"No listings found for event {event.get('event_id')}")
                return 0
            
            logger.info(
                f"Fetched {len(listings)} listings for event {event.get('event_id')} "
                f"(API latency: {api_latency:.0f}ms)"
            )
            
            # Parse and send each listing
            sent_count = 0
            for listing in listings:
                try:
                    price_event_dict = self.parse_listing(listing, event)
                    if self.send_price_event(price_event_dict):
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Error parsing listing: {e}")
                    self.metrics['total_errors'] += 1
                    continue
            
            # Flush producer to ensure all messages are sent
            self.producer.flush()
            
            logger.info(
                f"Processed {sent_count}/{len(listings)} listings for event {event.get('event_id')}"
            )
            
            return sent_count
            
        except Exception as e:
            self.metrics['total_errors'] += 1
            logger.error(f"Error processing event {event.get('event_id')}: {e}")
            return 0
    
    def run(self, events: List[Dict]):
        """
        Main polling loop.
        
        Args:
            events: List of event dictionaries to track
                Each event should have: event_id, name, venue, date
        """
        logger.info(
            f"Starting {self.source_name} producer, tracking {len(events)} events"
        )
        
        try:
            while True:
                cycle_start = time.time()
                
                for event in events:
                    self.process_event(event)
                
                # Log metrics periodically
                self.log_metrics()
                
                # Calculate sleep time
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.poll_interval - elapsed)
                
                if sleep_time > 0:
                    logger.info(
                        f"Polling cycle complete. Sleeping {sleep_time:.1f}s "
                        f"(elapsed: {elapsed:.1f}s)"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.warning(
                        f"Polling cycle took {elapsed:.1f}s, longer than interval "
                        f"({self.poll_interval}s). Continuing immediately."
                    )
                
        except KeyboardInterrupt:
            logger.info("Shutting down producer...")
            self.shutdown()
        except Exception as e:
            logger.error(f"Fatal error in producer loop: {e}")
            self.shutdown()
            raise
    
    def log_metrics(self):
        """Log current metrics."""
        logger.info(
            f"[{self.source_name} Metrics] "
            f"Events sent: {self.metrics['total_events_sent']}, "
            f"API calls: {self.metrics['total_api_calls']}, "
            f"Errors: {self.metrics['total_errors']}, "
            f"Avg API latency: {self.metrics['avg_api_latency_ms']:.0f}ms"
        )
    
    def shutdown(self):
        """Clean shutdown of producer."""
        logger.info("Closing Kafka producer...")
        self.producer.close()
        logger.info(f"{self.source_name} producer shut down")

