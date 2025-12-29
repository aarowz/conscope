#!/usr/bin/env python3
"""
Quick pipeline test - runs for 30 seconds then stops automatically.
"""

import time
import threading
import sys
from producers.mock_producer import MockProducer
from producers.test_events import TEST_EVENTS
from consumers.storage_consumer import StorageConsumer
from processors.price_processor import PriceProcessor
from consumers.alert_consumer import AlertConsumer

def main():
    print("=" * 70)
    print("🎫 ConScope Quick Pipeline Test (30 seconds)")
    print("=" * 70)
    print("\nStarting all components...\n")
    
    components = []
    
    # Start storage consumer
    print("💾 Starting Storage Consumer...")
    storage = StorageConsumer()
    components.append(storage)
    t1 = threading.Thread(target=storage.run, daemon=True)
    t1.start()
    time.sleep(2)
    
    # Start price processor
    print("⚙️  Starting Price Processor...")
    processor = PriceProcessor()
    components.append(processor)
    t2 = threading.Thread(target=processor.run, daemon=True)
    t2.start()
    time.sleep(2)
    
    # Start alert consumer
    print("🔔 Starting Alert Consumer...")
    alert = AlertConsumer()
    components.append(alert)
    t3 = threading.Thread(target=alert.run, daemon=True)
    t3.start()
    time.sleep(2)
    
    # Start mock producer
    print("🚀 Starting Mock Producer...")
    producer = MockProducer(poll_interval=3)  # Fast polling
    components.append(producer)
    t4 = threading.Thread(target=lambda: producer.run(TEST_EVENTS), daemon=True)
    t4.start()
    
    print("\n✅ All components started!")
    print("⏳ Running for 30 seconds...")
    print("   Watch the logs above to see price changes and alerts\n")
    
    # Run for 30 seconds
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    
    print("\n" + "=" * 70)
    print("🛑 Stopping all components...")
    print("=" * 70)
    
    # Shutdown all components
    for component in components:
        try:
            if hasattr(component, 'shutdown'):
                component.shutdown()
        except:
            pass
    
    print("\n✅ Test complete!")
    print("\n📊 Check results:")
    print("   docker exec conscope-postgres psql -U postgres -d conscope -c \\")
    print("     \"SELECT COUNT(*) FROM price_drop_alerts;\"")
    print("\n   Or view dashboard:")
    print("   streamlit run dashboard/app.py")

if __name__ == "__main__":
    main()

