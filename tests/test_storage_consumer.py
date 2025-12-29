#!/usr/bin/env python3
"""
Quick test script for storage consumer.

Tests the storage consumer with a few messages from Kafka.
"""

import sys
import time
from consumers.storage_consumer import StorageConsumer

def test_storage_consumer():
    """Test storage consumer with a few messages."""
    print("🧪 Testing Storage Consumer...")
    print("📊 Will process messages from Kafka and store in PostgreSQL\n")
    
    consumer = StorageConsumer()
    
    print("⏳ Consuming messages (will process up to 10 messages or timeout after 5 seconds)...\n")
    
    message_count = 0
    max_messages = 10
    start_time = time.time()
    timeout = 10  # seconds
    
    try:
        # Set consumer timeout to longer
        consumer.consumer.config['consumer_timeout_ms'] = timeout * 1000
        
        for message in consumer.consumer:
            if consumer.process_message(message):
                message_count += 1
                if message_count <= 5:  # Print first 5
                    print(f"✅ Processed message {message_count}")
                elif message_count == 6:
                    print("   ...")
            
            if message_count >= max_messages:
                break
            
            if time.time() - start_time > timeout:
                print(f"\n⏱️  Timeout after {timeout} seconds")
                break
        
        print(f"\n✅ Processed {message_count} messages")
        print(f"📈 Metrics: {consumer.metrics}")
        
        # Verify data in database
        print("\n🔍 Verifying data in database...")
        conn = consumer.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        print(f"   Events in database: {event_count}")
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        price_count = cursor.fetchone()[0]
        print(f"   Prices in database: {price_count}")
        
        if price_count > 0:
            cursor.execute("""
                SELECT event_name, COUNT(*) as price_count, 
                       MIN(price) as min_price, MAX(price) as max_price
                FROM price_history ph
                JOIN events e ON ph.event_id = e.event_id
                GROUP BY event_name
                ORDER BY price_count DESC
                LIMIT 5
            """)
            print("\n📊 Sample data:")
            for row in cursor.fetchall():
                print(f"   {row[0]}: {row[1]} prices, ${row[2]:.2f} - ${row[3]:.2f}")
        
        cursor.close()
        consumer.return_connection(conn)
        
        consumer.shutdown()
        print("\n✅ Storage consumer test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        consumer.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    test_storage_consumer()

