#!/usr/bin/env python3
"""
Quick test script for mock producer.

Runs the mock producer for a short time and verifies messages are sent to Kafka.
"""

import sys
import time
from producers.mock_producer import MockProducer
from producers.test_events import TEST_EVENTS

def test_mock_producer():
    """Test mock producer with a single polling cycle."""
    print("🧪 Testing Mock Producer...")
    print(f"📊 Will generate listings for {len(TEST_EVENTS)} test events\n")
    
    producer = MockProducer(poll_interval=5)  # Short interval for testing
    
    # Process events once
    total_listings = 0
    for event in TEST_EVENTS:
        count = producer.process_event(event)
        total_listings += count
        print(f"✅ Processed {count} listings for {event['name']}")
    
    print(f"\n✅ Total: {total_listings} listings sent to Kafka")
    print(f"📈 Metrics: {producer.metrics}")
    
    producer.shutdown()
    print("\n✅ Mock producer test completed successfully!")
    print("\n💡 To run continuously, use: python producers/mock_producer.py")

if __name__ == "__main__":
    try:
        test_mock_producer()
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

