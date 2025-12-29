# Mock Producer Guide

## Overview

The mock producer generates realistic test data for development and testing. Use it while waiting for API approval or when testing the pipeline without API access.

## Features

- ✅ Generates realistic price events (10-25 listings per event)
- ✅ Simulates price changes over time (60% drop, 30% same, 10% increase)
- ✅ Realistic sections, rows, seats (Floor, Lower Level, Upper Level, etc.)
- ✅ Price variations based on section type (Floor/VIP: $300-800, Lower: $150-400, Upper: $50-200)
- ✅ Includes fees and total prices
- ✅ Same format as real producer (easy to switch later)

## Quick Start

### 1. Make sure infrastructure is running

```bash
docker-compose ps
# Should show: kafka, postgres, zookeeper, kafka-ui all running
```

### 2. Run the mock producer

```bash
# Activate virtual environment
source venv/bin/activate

# Run mock producer
python producers/mock_producer.py
```

You should see output like:
```
INFO - Mock producer initialized (generating test data)
INFO - Starting mock producer, tracking 4 test events
INFO - Fetched 15 listings from Mock for event test_taylor_swift_2025
INFO - Processed 15/15 listings for event test_taylor_swift_2025
INFO - [mock Metrics] Events sent: 15, API calls: 1, Errors: 0
```

### 3. Verify messages in Kafka

**Option A: Using Kafka CLI**
```bash
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_prices \
  --from-beginning \
  --max-messages 5
```

**Option B: Using Kafka UI**
1. Open http://localhost:8080
2. Go to Topics → raw_prices
3. Click "Messages" tab
4. You should see JSON price events

## Configuration

### Customize Test Events

Edit `producers/test_events.py`:

```python
TEST_EVENTS = [
    {
        "event_id": "your_event_id",
        "name": "Your Event Name",
        "venue": "Venue Name",
        "date": "2025-05-15T19:00:00Z"
    }
]
```

### Adjust Polling Interval

Edit `producers/mock_producer.py` in the `main()` function:

```python
producer = MockProducer(poll_interval=30)  # Poll every 30 seconds
```

### Adjust Price Variation

```python
producer = MockProducer(price_variation_pct=0.20)  # 20% variation
```

## Price Simulation Details

The mock producer simulates realistic market behavior:

- **Price Drops (60%)**: Most listings decrease 2-10% over time (market saturation)
- **Price Stability (30%)**: Some listings stay the same
- **Price Increases (10%)**: Few listings increase 5-15% (demand spikes)

Each listing maintains a base price that changes over polling cycles, simulating real market dynamics.

## Example Output

```json
{
  "event_id": "test_taylor_swift_2025",
  "event_name": "Taylor Swift - Eras Tour",
  "venue": "MetLife Stadium",
  "event_date": "2025-05-15T19:00:00Z",
  "source": "mock",
  "section": "Floor 2",
  "row": "15",
  "seat": "8",
  "price": 425.50,
  "fees": 63.83,
  "total_price": 489.33,
  "timestamp": "2025-12-24T20:00:00",
  "listing_id": "mock_test_taylor_swift_2025_0_1234567890",
  "listing_url": "https://mock-tickets.com/event/test_taylor_swift_2025/listing/0",
  "quantity": 1,
  "delivery_method": "mobile"
}
```

## Testing Price Change Detection

The mock producer is perfect for testing price change detection:

1. **Run mock producer** - Generates initial prices
2. **Wait a few polling cycles** - Prices will change (some drop, some increase)
3. **Run price processor** - Should detect price changes
4. **Check alerts** - Price drops should trigger alerts

## Switching to Real Producer

Once your SeatGeek API is approved:

1. Add your API key to `.env`:
   ```bash
   SEATGEEK_API_KEY=your_actual_key
   ```

2. Configure real events in `producers/config.py`:
   ```python
   DEFAULT_EVENTS = [
       {
           "event_id": "6174046",  # Real SeatGeek event ID
           "name": "Taylor Swift - Eras Tour",
           "venue": "MetLife Stadium",
           "date": "2025-05-15T19:00:00Z"
       }
   ]
   ```

3. Run the real producer:
   ```bash
   python producers/seatgeek_producer.py
   ```

The format is identical, so everything else (consumers, processors) works the same!

## Troubleshooting

### "ModuleNotFoundError: No module named 'kafka'"

If you see Kafka library errors, try:

```bash
# Option 1: Use Python 3.10 or 3.11 (kafka-python works better)
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Option 2: Use confluent-kafka (more actively maintained)
pip install confluent-kafka
# Then update imports in base_producer.py to use confluent_kafka
```

### "Connection refused" to Kafka

```bash
# Check if Kafka is running
docker-compose ps kafka

# Restart if needed
docker-compose restart kafka
```

### No messages appearing

- Check producer logs for errors
- Verify Kafka topics exist: `docker exec conscope-kafka kafka-topics --list --bootstrap-server localhost:9092`
- Check Kafka UI at http://localhost:8080

## Next Steps

Once the mock producer is working:

1. ✅ **Test storage consumer** - Save prices to PostgreSQL
2. ✅ **Test price processor** - Detect price changes
3. ✅ **Test alert consumer** - Send notifications
4. ✅ **Build dashboard** - Visualize prices

The mock producer generates enough realistic data to test the entire pipeline!

