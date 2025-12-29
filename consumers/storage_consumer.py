#!/usr/bin/env python3
"""
Storage consumer for ConScope.

This consumer reads price events from Kafka and stores them in PostgreSQL.
It handles event creation, price history insertion, and error recovery.
"""

import os
import logging
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import pool
from psycopg2.errors import UniqueViolation, ForeignKeyViolation
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StorageConsumer:
    """
    Consumer that stores price events from Kafka into PostgreSQL.
    
    Reads from raw_prices topic and stores:
    - Events in events table (if not exists)
    - Prices in price_history table
    """
    
    def __init__(
        self,
        kafka_broker: str = None,
        topic_name: str = 'raw_prices',
        db_config: Dict = None
    ):
        """
        Initialize storage consumer.
        
        Args:
            kafka_broker: Kafka broker address
            topic_name: Kafka topic to consume from
            db_config: Database configuration dict (or None to use .env)
        """
        # Kafka consumer
        kafka_broker = kafka_broker or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=kafka_broker,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='storage_consumer',
            auto_offset_reset='earliest',  # Start from beginning for first run
            enable_auto_commit=True
            # Removed consumer_timeout_ms to wait indefinitely for messages
        )
        
        # Database connection pool
        if db_config is None:
            db_config = {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "database": os.getenv("POSTGRES_DB", "conscope"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", "password"),
            }
        
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # min connections
                5,  # max connections
                **db_config
            )
            logger.info(f"Connected to PostgreSQL at {db_config['host']}:{db_config['port']}")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
        
        # Metrics tracking
        self.metrics = {
            'total_messages_processed': 0,
            'total_events_created': 0,
            'total_prices_stored': 0,
            'total_errors': 0,
            'duplicate_skips': 0
        }
        
        logger.info(f"Storage consumer initialized (topic: {topic_name})")
    
    def get_connection(self):
        """Get a connection from the pool."""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return a connection to the pool."""
        self.connection_pool.putconn(conn)
    
    def ensure_event_exists(self, event_data: Dict) -> bool:
        """
        Insert event into events table if it doesn't exist.
        
        Args:
            event_data: Price event dictionary
            
        Returns:
            True if event exists or was created, False on error
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            event_id = event_data.get('event_id')
            event_name = event_data.get('event_name', '')
            venue = event_data.get('venue', '')
            event_date_str = event_data.get('event_date')
            
            # Parse event_date
            if isinstance(event_date_str, str):
                try:
                    event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                except:
                    event_date = datetime.now()
            else:
                event_date = datetime.now()
            
            # Try to insert event (ON CONFLICT handles duplicates)
            cursor.execute("""
                INSERT INTO events (event_id, event_name, venue, event_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (event_id) DO UPDATE
                SET last_updated = NOW()
                RETURNING id;
            """, (event_id, event_name, venue, event_date))
            
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                # Check if this was a new event (id might be new or existing)
                cursor.execute("SELECT id FROM events WHERE event_id = %s", (event_id,))
                existing = cursor.fetchone()
                if existing and existing[0] == result[0]:
                    # Check if it was just created (created_at == last_updated)
                    cursor.execute("""
                        SELECT created_at, last_updated 
                        FROM events 
                        WHERE event_id = %s
                    """, (event_id,))
                    times = cursor.fetchone()
                    if times and times[0] == times[1]:
                        self.metrics['total_events_created'] += 1
                        logger.debug(f"Created new event: {event_id}")
            
            cursor.close()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error ensuring event exists: {e}")
            self.metrics['total_errors'] += 1
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def store_price(self, event_data: Dict) -> bool:
        """
        Store price in price_history table.
        
        Args:
            event_data: Price event dictionary
            
        Returns:
            True if stored successfully, False otherwise
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Parse timestamp
            timestamp_str = event_data.get('timestamp')
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Insert price history
            cursor.execute("""
                INSERT INTO price_history 
                (event_id, source, section, row, seat, price, fees, total_price, 
                 timestamp, listing_id, listing_url, quantity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_data.get('event_id'),
                event_data.get('source', 'unknown'),
                event_data.get('section'),
                event_data.get('row'),
                event_data.get('seat'),
                float(event_data.get('price', 0)),
                float(event_data.get('fees', 0)) if event_data.get('fees') else None,
                float(event_data.get('total_price', event_data.get('price', 0))),
                timestamp,
                event_data.get('listing_id', ''),
                event_data.get('listing_url', ''),
                int(event_data.get('quantity', 1))
            ))
            
            conn.commit()
            self.metrics['total_prices_stored'] += 1
            cursor.close()
            return True
            
        except UniqueViolation:
            # Duplicate listing_id (same listing, different timestamp)
            # This is okay - we'll store it anyway as price history
            if conn:
                conn.rollback()
            # Try without listing_id uniqueness constraint
            logger.debug(f"Duplicate listing_id detected: {event_data.get('listing_id')}")
            self.metrics['duplicate_skips'] += 1
            return False
        except ForeignKeyViolation:
            if conn:
                conn.rollback()
            logger.warning(f"Foreign key violation - event {event_data.get('event_id')} doesn't exist")
            # Try to create event first, then retry
            if self.ensure_event_exists(event_data):
                return self.store_price(event_data)  # Retry
            return False
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error storing price: {e}")
            self.metrics['total_errors'] += 1
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def process_message(self, message) -> bool:
        """
        Process a single Kafka message.
        
        Args:
            message: Kafka message object
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            price_event = message.value
            
            # Ensure event exists first
            if not self.ensure_event_exists(price_event):
                logger.warning(f"Failed to ensure event exists: {price_event.get('event_id')}")
                return False
            
            # Store price
            if self.store_price(price_event):
                self.metrics['total_messages_processed'] += 1
                logger.debug(
                    f"Stored price: {price_event.get('event_id')} | "
                    f"{price_event.get('section')} | ${price_event.get('price')}"
                )
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.metrics['total_errors'] += 1
            return False
    
    def log_metrics(self):
        """Log current metrics."""
        logger.info(
            f"[Storage Consumer Metrics] "
            f"Messages processed: {self.metrics['total_messages_processed']}, "
            f"Events created: {self.metrics['total_events_created']}, "
            f"Prices stored: {self.metrics['total_prices_stored']}, "
            f"Errors: {self.metrics['total_errors']}, "
            f"Duplicates skipped: {self.metrics['duplicate_skips']}"
        )
    
    def run(self):
        """Main consumption loop."""
        logger.info("Starting storage consumer...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            message_count = 0
            batch_start = datetime.now()
            
            for message in self.consumer:
                self.process_message(message)
                message_count += 1
                
                # Log metrics every 50 messages
                if message_count % 50 == 0:
                    self.log_metrics()
                
                # Log batch summary every 5 minutes
                elapsed = (datetime.now() - batch_start).total_seconds()
                if elapsed > 300:  # 5 minutes
                    logger.info(
                        f"Processed {message_count} messages in last 5 minutes "
                        f"({message_count / elapsed * 60:.1f} messages/min)"
                    )
                    batch_start = datetime.now()
                    message_count = 0
                    
        except KeyboardInterrupt:
            logger.info("Shutting down storage consumer...")
        except Exception as e:
            logger.error(f"Fatal error in consumer loop: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of consumer."""
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        
        if hasattr(self, 'connection_pool'):
            logger.info("Closing database connection pool...")
            self.connection_pool.closeall()
        
        # Final metrics
        self.log_metrics()
        logger.info("Storage consumer shut down")


def main():
    """Main entry point for storage consumer."""
    import sys
    
    try:
        consumer = StorageConsumer()
        consumer.run()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

