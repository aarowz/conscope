#!/usr/bin/env python3
"""
Complete pipeline test script for ConScope.

This script runs all components together to test the complete system:
1. Mock Producer (generates price events)
2. Storage Consumer (stores in PostgreSQL)
3. Price Processor (detects price changes)
4. Alert Consumer (sends notifications)

Run this script and let it run for 60-90 seconds to see the full pipeline in action.
"""

import time
import signal
import sys
import threading
from datetime import datetime

# Import all components
from producers.mock_producer import MockProducer
from producers.test_events import TEST_EVENTS
from consumers.storage_consumer import StorageConsumer
from processors.price_processor import PriceProcessor
from consumers.alert_consumer import AlertConsumer

# Global flags for graceful shutdown
running = True
components = []

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n🛑 Shutting down all components...")
    running = False
    for component in components:
        try:
            if hasattr(component, 'shutdown'):
                component.shutdown()
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_producer():
    """Run mock producer."""
    print("🚀 Starting Mock Producer...")
    producer = MockProducer(poll_interval=5)  # Fast polling for testing
    components.append(producer)
    try:
        producer.run(TEST_EVENTS)
    except Exception as e:
        print(f"❌ Producer error: {e}")

def run_storage_consumer():
    """Run storage consumer."""
    print("💾 Starting Storage Consumer...")
    consumer = StorageConsumer()
    components.append(consumer)
    try:
        consumer.run()
    except Exception as e:
        print(f"❌ Storage Consumer error: {e}")

def run_price_processor():
    """Run price processor."""
    print("⚙️  Starting Price Processor...")
    processor = PriceProcessor()
    components.append(processor)
    try:
        processor.run()
    except Exception as e:
        print(f"❌ Price Processor error: {e}")

def run_alert_consumer():
    """Run alert consumer."""
    print("🔔 Starting Alert Consumer...")
    consumer = AlertConsumer()
    components.append(consumer)
    try:
        consumer.run()
    except Exception as e:
        print(f"❌ Alert Consumer error: {e}")

def main():
    """Main test function."""
    print("=" * 70)
    print("🎫 ConScope Complete Pipeline Test")
    print("=" * 70)
    print("\nThis test will run all components together:")
    print("  1. Mock Producer - Generates price events")
    print("  2. Storage Consumer - Stores events in PostgreSQL")
    print("  3. Price Processor - Detects price changes")
    print("  4. Alert Consumer - Sends notifications")
    print("\n⏱️  Let it run for 60-90 seconds to see price drops and alerts")
    print("   Press Ctrl+C to stop\n")
    print("-" * 70)
    
    # Start all components in separate threads
    threads = []
    
    # Storage consumer (reads from beginning)
    t1 = threading.Thread(target=run_storage_consumer, daemon=True)
    t1.start()
    threads.append(t1)
    time.sleep(2)  # Give storage consumer time to start
    
    # Price processor
    t2 = threading.Thread(target=run_price_processor, daemon=True)
    t2.start()
    threads.append(t2)
    time.sleep(2)  # Give processor time to start
    
    # Alert consumer
    t3 = threading.Thread(target=run_alert_consumer, daemon=True)
    t3.start()
    threads.append(t3)
    time.sleep(2)  # Give alert consumer time to start
    
    # Mock producer (last, so it generates new messages)
    t4 = threading.Thread(target=run_producer, daemon=True)
    t4.start()
    threads.append(t4)
    
    print("\n✅ All components started!")
    print("📊 Watch the logs above to see:")
    print("   - Price events being generated")
    print("   - Prices being stored")
    print("   - Price changes being detected")
    print("   - Price drop alerts being sent")
    print("\n⏳ Running... (Press Ctrl+C to stop)\n")
    
    # Keep main thread alive
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

