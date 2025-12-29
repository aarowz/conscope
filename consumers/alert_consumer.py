#!/usr/bin/env python3
"""
Alert consumer for ConScope.

This consumer reads price drop alerts from Kafka and sends notifications
via Discord webhooks. It also stores alerts in PostgreSQL.
"""

import os
import logging
import requests
import json
from datetime import datetime
from typing import Dict, Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool
from psycopg2.errors import UniqueViolation

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertConsumer:
    """
    Consumer that processes price drop alerts and sends notifications.
    
    Reads from price_alerts topic and:
    - Sends Discord webhook notifications
    - Stores alerts in PostgreSQL alerts table
    - Tracks alert triggers
    """
    
    def __init__(
        self,
        kafka_broker: str = None,
        topic_name: str = 'price_alerts',
        discord_webhook_url: str = None,
        db_config: Dict = None
    ):
        """
        Initialize alert consumer.
        
        Args:
            kafka_broker: Kafka broker address
            topic_name: Kafka topic to consume from
            discord_webhook_url: Discord webhook URL for notifications
            db_config: Database configuration dict (or None to use .env)
        """
        kafka_broker = kafka_broker or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        # Kafka consumer
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=kafka_broker,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='alert_consumer',
            auto_offset_reset='latest',  # Start from latest for real-time alerts
            enable_auto_commit=True
        )
        
        # Discord webhook URL
        self.discord_webhook_url = discord_webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        if not self.discord_webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL not set - alerts will not be sent to Discord")
        
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
            'total_alerts_processed': 0,
            'discord_notifications_sent': 0,
            'alerts_stored': 0,
            'total_errors': 0,
            'discord_errors': 0
        }
        
        logger.info(f"Alert consumer initialized (topic: {topic_name})")
    
    def get_connection(self):
        """Get a connection from the pool."""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return a connection to the pool."""
        self.connection_pool.putconn(conn)
    
    def format_discord_message(self, alert: Dict) -> Dict:
        """
        Format alert as Discord embed message.
        
        Args:
            alert: Alert event dictionary
            
        Returns:
            Discord webhook payload dictionary
        """
        event_name = alert.get('event_name', 'Unknown Event')
        venue = alert.get('venue', 'Unknown Venue')
        section = alert.get('section', 'Unknown')
        row = alert.get('row', 'N/A')
        seat = alert.get('seat', 'N/A')
        
        old_price = alert.get('old_price', 0)
        new_price = alert.get('new_price', 0)
        drop_amount = alert.get('drop_amount', 0)
        drop_percent = alert.get('drop_percent', 0)
        
        listing_url = alert.get('listing_url', '#')
        source = alert.get('source', 'unknown').upper()
        
        # Create Discord embed
        embed = {
            "title": "🚨 Price Drop Alert!",
            "description": f"**{event_name}**",
            "color": 0x00ff00,  # Green color
            "fields": [
                {
                    "name": "📍 Venue",
                    "value": venue,
                    "inline": True
                },
                {
                    "name": "🎫 Section",
                    "value": f"{section} Row {row} Seat {seat}",
                    "inline": True
                },
                {
                    "name": "💰 Price Change",
                    "value": f"${old_price:.2f} → **${new_price:.2f}**",
                    "inline": False
                },
                {
                    "name": "📉 Drop",
                    "value": f"${drop_amount:.2f} ({drop_percent:.1f}%)",
                    "inline": True
                },
                {
                    "name": "🔗 Source",
                    "value": source,
                    "inline": True
                }
            ],
            "timestamp": alert.get('alert_timestamp', datetime.now().isoformat()),
            "footer": {
                "text": "ConScope Price Monitor"
            }
        }
        
        # Add buy link if available
        if listing_url and listing_url != '#':
            embed["url"] = listing_url
        
        return {
            "embeds": [embed]
        }
    
    def send_discord_notification(self, alert: Dict) -> bool:
        """
        Send alert notification to Discord webhook.
        
        Args:
            alert: Alert event dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.discord_webhook_url:
            logger.debug("Discord webhook URL not configured, skipping notification")
            return False
        
        try:
            payload = self.format_discord_message(alert)
            response = requests.post(
                self.discord_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.info(f"Discord notification sent for {alert.get('event_name', 'Unknown')}")
                self.metrics['discord_notifications_sent'] += 1
                return True
            else:
                logger.error(f"Discord webhook returned status {response.status_code}: {response.text}")
                self.metrics['discord_errors'] += 1
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Discord notification: {e}")
            self.metrics['discord_errors'] += 1
            return False
    
    def store_alert(self, alert: Dict) -> bool:
        """
        Store alert in PostgreSQL.
        
        Args:
            alert: Alert event dictionary
            
        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert into price_drop_alerts table
            insert_alert = """
                INSERT INTO price_drop_alerts (
                    event_id, alert_type, alert_timestamp, 
                    old_price, new_price, drop_amount, drop_percent,
                    section, row, seat, source, listing_id, listing_url
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING alert_id
            """
            
            cursor.execute(insert_alert, (
                alert.get('event_id'),
                alert.get('alert_type', 'price_drop'),
                alert.get('alert_timestamp', datetime.now().isoformat()),
                alert.get('old_price'),
                alert.get('new_price'),
                alert.get('drop_amount'),
                alert.get('drop_percent'),
                alert.get('section'),
                alert.get('row'),
                alert.get('seat'),
                alert.get('source'),
                alert.get('listing_id'),
                alert.get('listing_url')
            ))
            
            alert_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            logger.debug(f"Alert stored in database (alert_id: {alert_id})")
            self.metrics['alerts_stored'] += 1
            return True
            
        except UniqueViolation:
            # Alert already exists (shouldn't happen, but handle gracefully)
            logger.warning(f"Alert already exists for listing {alert.get('listing_id')}")
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
            self.metrics['total_errors'] += 1
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def process_alert(self, alert: Dict) -> bool:
        """
        Process a single alert: send notification and store in DB.
        
        Args:
            alert: Alert event dictionary
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        # Send Discord notification
        if not self.send_discord_notification(alert):
            success = False
        
        # Store in database
        if not self.store_alert(alert):
            success = False
        
        return success
    
    def log_metrics(self):
        """Log current metrics."""
        logger.info(
            f"[Alert Consumer Metrics] "
            f"Alerts processed: {self.metrics['total_alerts_processed']}, "
            f"Discord sent: {self.metrics['discord_notifications_sent']}, "
            f"Stored: {self.metrics['alerts_stored']}, "
            f"Errors: {self.metrics['total_errors']}, "
            f"Discord errors: {self.metrics['discord_errors']}"
        )
    
    def run(self):
        """Main consumption loop."""
        logger.info("Starting alert consumer...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            message_count = 0
            
            for message in self.consumer:
                alert = message.value
                
                # Process the alert
                self.process_alert(alert)
                
                self.metrics['total_alerts_processed'] += 1
                message_count += 1
                
                # Log metrics every 10 alerts
                if message_count % 10 == 0:
                    self.log_metrics()
                    
        except KeyboardInterrupt:
            logger.info("Shutting down alert consumer...")
        except Exception as e:
            logger.error(f"Fatal error in consumer loop: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of consumer."""
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        
        # Close database pool
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
        
        # Final metrics
        self.log_metrics()
        logger.info("Alert consumer shut down")


def main():
    """Main entry point for alert consumer."""
    import sys
    
    try:
        consumer = AlertConsumer()
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

