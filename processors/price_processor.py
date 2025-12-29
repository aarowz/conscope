#!/usr/bin/env python3
"""
Price processor for ConScope.

This processor reads price events from Kafka, detects price changes,
and publishes alerts when prices drop. It maintains an in-memory cache
of last seen prices to compare against new prices.
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import json
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PriceProcessor:
    """
    Processor that detects price changes and publishes alerts.
    
    Reads from raw_prices topic and:
    - Maintains cache of last seen prices per listing
    - Detects price changes (increases and decreases)
    - Publishes all processed events to processed_prices topic
    - Publishes price drops to price_alerts topic
    """
    
    def __init__(
        self,
        kafka_broker: str = None,
        input_topic: str = 'raw_prices',
        processed_topic: str = 'processed_prices',
        alerts_topic: str = 'price_alerts'
    ):
        """
        Initialize price processor.
        
        Args:
            kafka_broker: Kafka broker address
            input_topic: Topic to read from (raw_prices)
            processed_topic: Topic to publish processed events to
            alerts_topic: Topic to publish price alerts to
        """
        kafka_broker = kafka_broker or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        # Kafka consumer (reads from raw_prices)
        self.consumer = KafkaConsumer(
            input_topic,
            bootstrap_servers=kafka_broker,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='price_processor',
            auto_offset_reset='latest',  # Start from latest for real-time processing
            enable_auto_commit=True
        )
        
        # Kafka producers (publish to processed_prices and price_alerts)
        self.processed_producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=3,
            compression_type='snappy'
        )
        
        self.alerts_producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=3,
            compression_type='snappy'
        )
        
        # In-memory cache: {listing_key: last_price_info}
        # listing_key format: "{event_id}_{source}_{section}_{row}_{seat}"
        self.price_cache: Dict[str, Dict] = {}
        
        self.processed_topic = processed_topic
        self.alerts_topic = alerts_topic
        
        # Metrics tracking
        self.metrics = {
            'total_events_processed': 0,
            'price_changes_detected': 0,
            'price_drops_detected': 0,
            'price_increases_detected': 0,
            'new_listings': 0,
            'total_errors': 0
        }
        
        logger.info(f"Price processor initialized (input: {input_topic}, processed: {processed_topic}, alerts: {alerts_topic})")
    
    def make_listing_key(self, event: Dict) -> str:
        """
        Create unique key for a listing.
        
        Args:
            event: Price event dictionary
            
        Returns:
            Unique string key for the listing
        """
        return f"{event.get('event_id', '')}_{event.get('source', '')}_{event.get('section', '')}_{event.get('row', '')}_{event.get('seat', '')}"
    
    def process_price_event(self, event: Dict) -> Optional[Dict]:
        """
        Process a single price event and detect changes.
        
        Args:
            event: Price event dictionary from Kafka
            
        Returns:
            Alert event dictionary if price dropped, None otherwise
        """
        try:
            listing_key = self.make_listing_key(event)
            new_price = float(event.get('price', 0))
            
            if new_price <= 0:
                logger.warning(f"Invalid price {new_price} for listing {listing_key}")
                return None
            
            # Check if we've seen this listing before
            if listing_key in self.price_cache:
                cached_info = self.price_cache[listing_key]
                old_price = cached_info.get('price', new_price)
                
                if new_price != old_price:
                    # Price changed
                    price_change = new_price - old_price
                    change_pct = (price_change / old_price) * 100
                    
                    self.metrics['price_changes_detected'] += 1
                    
                    logger.info(
                        f"Price change: {event.get('event_name', 'Unknown')} | "
                        f"{event.get('section', 'Unknown')} Row {event.get('row', 'Unknown')} | "
                        f"${old_price:.2f} → ${new_price:.2f} ({change_pct:+.1f}%)"
                    )
                    
                    # If price dropped, create alert
                    if new_price < old_price:
                        self.metrics['price_drops_detected'] += 1
                        
                        drop_amount = old_price - new_price
                        drop_pct = abs(change_pct)
                        
                        alert_event = {
                            **event,  # Include all original fields
                            "old_price": old_price,
                            "new_price": new_price,
                            "drop_amount": drop_amount,
                            "drop_percent": drop_pct,
                            "alert_timestamp": datetime.now().isoformat(),
                            "alert_type": "price_drop"
                        }
                        
                        logger.info(
                            f"🚨 PRICE DROP ALERT: {event.get('event_name', 'Unknown')} | "
                            f"{event.get('section', 'Unknown')} | "
                            f"${old_price:.2f} → ${new_price:.2f} (${drop_amount:.2f} drop, {drop_pct:.1f}%)"
                        )
                        
                        return alert_event
                    else:
                        # Price increased
                        self.metrics['price_increases_detected'] += 1
            else:
                # New listing - add to cache
                self.metrics['new_listings'] += 1
                logger.debug(f"New listing: {listing_key} at ${new_price:.2f}")
            
            # Update cache with current price
            self.price_cache[listing_key] = {
                'price': new_price,
                'timestamp': event.get('timestamp'),
                'listing_id': event.get('listing_id')
            }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing price event: {e}")
            self.metrics['total_errors'] += 1
            return None
    
    def publish_processed_event(self, event: Dict):
        """Publish processed event to processed_prices topic."""
        try:
            self.processed_producer.send(self.processed_topic, value=event)
        except KafkaError as e:
            logger.error(f"Error publishing to processed_prices: {e}")
            self.metrics['total_errors'] += 1
    
    def publish_alert(self, alert_event: Dict):
        """Publish price drop alert to price_alerts topic."""
        try:
            self.alerts_producer.send(self.alerts_topic, value=alert_event)
            self.alerts_producer.flush()  # Ensure alert is sent immediately
            logger.debug(f"Alert published for {alert_event.get('event_name', 'Unknown')}")
        except KafkaError as e:
            logger.error(f"Error publishing alert: {e}")
            self.metrics['total_errors'] += 1
    
    def log_metrics(self):
        """Log current metrics."""
        logger.info(
            f"[Price Processor Metrics] "
            f"Events processed: {self.metrics['total_events_processed']}, "
            f"Price changes: {self.metrics['price_changes_detected']}, "
            f"Drops: {self.metrics['price_drops_detected']}, "
            f"Increases: {self.metrics['price_increases_detected']}, "
            f"New listings: {self.metrics['new_listings']}, "
            f"Errors: {self.metrics['total_errors']}"
        )
    
    def run(self):
        """Main processing loop."""
        logger.info("Starting price processor...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            message_count = 0
            
            for message in self.consumer:
                event = message.value
                
                # Process the event
                alert_event = self.process_price_event(event)
                
                # Publish to processed_prices (all events)
                self.publish_processed_event(event)
                
                # Publish alert if price dropped
                if alert_event:
                    self.publish_alert(alert_event)
                
                self.metrics['total_events_processed'] += 1
                message_count += 1
                
                # Log metrics every 100 messages
                if message_count % 100 == 0:
                    self.log_metrics()
                
                # Flush producers periodically
                if message_count % 50 == 0:
                    self.processed_producer.flush()
                    
        except KeyboardInterrupt:
            logger.info("Shutting down price processor...")
        except Exception as e:
            logger.error(f"Fatal error in processor loop: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of processor."""
        logger.info("Closing Kafka consumer and producers...")
        self.consumer.close()
        self.processed_producer.close()
        self.alerts_producer.close()
        
        # Final metrics
        self.log_metrics()
        logger.info(f"Price processor shut down. Cache size: {len(self.price_cache)} listings")


def main():
    """Main entry point for price processor."""
    import sys
    
    try:
        processor = PriceProcessor()
        processor.run()
    except KeyboardInterrupt:
        logger.info("Processor stopped by user")
    except Exception as e:
        logger.error(f"Processor error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

