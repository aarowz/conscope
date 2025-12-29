#!/usr/bin/env python3
"""
Test script for price processor.

This script runs the mock producer and price processor together
to verify price change detection works correctly.
"""

import time
import signal
import sys
from threading import Thread
from producers.mock_producer import MockProducer
from producers.test_events import TEST_EVENTS
from processors.price_processor import PriceProcessor
from kafka import KafkaConsumer
import json

def test_price_processor():
    """Test price processor with mock producer."""
    print("=" * 60)
    print("Testing Price Processor")
    print("=" * 60)
    
    # Start mock producer in background thread
    print("\n1. Starting mock producer...")
    producer = MockProducer(poll_interval=5)  # Fast polling for testing
    producer_thread = Thread(target=lambda: producer.run(TEST_EVENTS), daemon=True)
    producer_thread.start()
    
    # Wait a bit for some messages to be produced
    print("   Waiting 10 seconds for producer to generate messages...")
    time.sleep(10)
    
    # Start price processor
    print("\n2. Starting price processor...")
    print("   (This will process messages and detect price changes)")
    print("   Press Ctrl+C after ~30 seconds to stop\n")
    
    try:
        processor = PriceProcessor()
        processor.run()
    except KeyboardInterrupt:
        print("\n\n3. Stopping test...")
        producer.shutdown()
        processor.shutdown()
        print("Test complete!")

if __name__ == "__main__":
    test_price_processor()

