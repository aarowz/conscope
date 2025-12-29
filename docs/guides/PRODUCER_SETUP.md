# Producer Setup Guide

## Overview

The SeatGeek producer is now ready to use! It polls the SeatGeek API for ticket listings and publishes price events to Kafka.

## Files Created

1. **`producers/base_producer.py`** - Abstract base class with common functionality
   - Kafka connection management
   - Error handling and retries
   - Metrics tracking
   - Polling loop

2. **`producers/seatgeek_producer.py`** - SeatGeek-specific implementation
   - Fetches listings from SeatGeek API
   - Parses listings into PriceEvent format
   - Handles rate limits and errors

3. **`producers/config.py`** - Configuration management
   - API keys from environment variables
   - Kafka broker settings
   - Default events to track

## Setup Steps

### 1. Get SeatGeek API Key

1. Go to https://platform.seatgeek.com/
2. Sign up for a free account
3. Create a new application to get your `client_id` (API key)
4. Add it to your `.env` file:
   ```
   SEATGEEK_API_KEY=your_client_id_here
   ```

### 2. Configure Events to Track

Edit `producers/config.py` and add events to `DEFAULT_EVENTS`:

```python
DEFAULT_EVENTS = [
    {
        "event_id": "6174046",  # SeatGeek event ID
        "name": "Taylor Swift - Eras Tour",
        "venue": "MetLife Stadium",
        "date": "2025-05-15T19:00:00Z"
    }
]
```

**How to find SeatGeek event IDs:**
- Visit seatgeek.com and search for an event
- The event ID is in the URL: `seatgeek.com/event-name-tickets/event-id`
- Or use the SeatGeek API search endpoint

### 3. Start Infrastructure

```bash
# Make sure Kafka and PostgreSQL are running
docker-compose up -d

# Initialize database (if not done already)
python scripts/init_db.py

# Create Kafka topics (if not done already)
python kafka_setup/create_topics.py
```

### 4. Run the Producer

```bash
# From project root
python producers/seatgeek_producer.py
```

The producer will:
- Poll SeatGeek API every 60 seconds (configurable)
- Fetch listings for all configured events
- Publish price events to Kafka `raw_prices` topic
- Log metrics and errors

## Testing

### Verify Producer is Working

1. **Check logs** - You should see:
   ```
   INFO - Fetched X listings from SeatGeek for event Y
   INFO - Processed X/Y listings for event Y
   ```

2. **Check Kafka** - View messages in Kafka:
   ```bash
   docker exec -it conscope-kafka kafka-console-consumer \
     --bootstrap-server localhost:9092 \
     --topic raw_prices \
     --from-beginning
   ```

3. **Check Kafka UI** - Visit http://localhost:8080
   - Navigate to Topics → raw_prices
   - View messages and consumer groups

### Test with a Real Event

1. Find a popular event on SeatGeek (e.g., upcoming concert)
2. Get the event ID from the URL
3. Add it to `DEFAULT_EVENTS` in `producers/config.py`
4. Run the producer
5. Verify you see listings in Kafka

## Configuration Options

### Poll Interval

Change polling frequency in `.env`:
```bash
POLL_INTERVAL_SECONDS=30  # Poll every 30 seconds
```

Or pass when initializing:
```python
producer = SeatGeekProducer(poll_interval=30)
```

### Kafka Broker

Default: `localhost:9092`

Override in `.env`:
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Error Handling

The producer handles:
- **API rate limits** - Logs warning, continues polling
- **Network errors** - Retries with exponential backoff
- **Invalid data** - Skips bad listings, logs error
- **Kafka errors** - Retries up to 3 times

## Metrics

The producer tracks:
- `total_events_sent` - Total price events published
- `total_api_calls` - Number of API requests
- `total_errors` - Error count
- `avg_api_latency_ms` - Average API response time

Metrics are logged periodically during operation.

## Next Steps

Once the producer is working:

1. **Build storage consumer** - Save prices to PostgreSQL
2. **Build price processor** - Detect price changes
3. **Build alert consumer** - Send notifications
4. **Build dashboard** - Visualize prices

## Troubleshooting

### "SEATGEEK_API_KEY not found"
- Make sure `.env` file exists and contains `SEATGEEK_API_KEY=...`
- Or set environment variable: `export SEATGEEK_API_KEY=your_key`

### "No events configured"
- Add events to `DEFAULT_EVENTS` in `producers/config.py`
- Or pass events directly when calling `producer.run(events)`

### "Connection refused" to Kafka
- Make sure Kafka is running: `docker-compose ps kafka`
- Check Kafka logs: `docker-compose logs kafka`

### "No listings found"
- Verify event ID is correct
- Check if event has tickets available on SeatGeek
- Some events may not have listings yet

### Rate limiting
- SeatGeek free tier: 5,000 requests/hour
- Producer polls every 60s, so ~60 requests/hour per event
- If tracking many events, you may hit limits
- Consider increasing poll interval or upgrading API tier

## Example: Custom Event List

```python
from seatgeek_producer import SeatGeekProducer

# Custom events
events = [
    {
        "event_id": "123456",
        "name": "Olivia Rodrigo - Guts World Tour",
        "venue": "Madison Square Garden",
        "date": "2025-06-20T20:00:00Z"
    },
    {
        "event_id": "789012",
        "name": "The Weeknd - After Hours Til Dawn Tour",
        "venue": "Staples Center",
        "date": "2025-07-10T19:30:00Z"
    }
]

producer = SeatGeekProducer()
producer.run(events)
```

