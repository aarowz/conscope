# Testing Status - ConScope Producer

## ✅ Completed Setup Steps

1. **✅ Created `.env` file** - Configuration file created
2. **✅ Started Docker services** - All services running:
   - Kafka (port 9092) ✅ Healthy
   - Zookeeper (port 2181) ✅ Healthy  
   - PostgreSQL (port 5432) ✅ Healthy
   - Kafka UI (port 8080) ✅ Running

3. **✅ Database initialized** - All tables created:
   - events
   - price_history
   - alerts
   - alert_triggers
   - system_metrics

4. **✅ Kafka topics created** - All topics ready:
   - raw_prices (4 partitions)
   - processed_prices (3 partitions)
   - price_alerts (2 partitions)
   - system_metrics (1 partition)

5. **✅ Dependencies installed** - Python packages installed in venv

## 🔧 Next Steps to Test Producer

### Step 1: Get SeatGeek API Key

1. Go to https://platform.seatgeek.com/
2. Sign up/login for a free account
3. Create a new application
4. Copy your `client_id` (this is your API key)

### Step 2: Add API Key to .env

Edit `.env` file and replace the placeholder:

```bash
# Change this line:
SEATGEEK_API_KEY=your_seatgeek_client_id_here

# To your actual API key:
SEATGEEK_API_KEY=your_actual_client_id
```

### Step 3: Find a Test Event

**Option A: Use SeatGeek Website**
1. Visit https://seatgeek.com
2. Search for an event (e.g., "Taylor Swift", "Olivia Rodrigo", "The Weeknd")
3. Click on an event
4. Look at the URL: `seatgeek.com/event-name-tickets/EVENT_ID`
5. Copy the EVENT_ID number

**Option B: Use SeatGeek API Search** (after you have API key)
```bash
# Replace YOUR_API_KEY with your actual key
curl "https://api.seatgeek.com/2/events?client_id=YOUR_API_KEY&q=taylor+swift&per_page=5"
```

Look for the `id` field in the response.

### Step 4: Configure Event in producers/config.py

Edit `producers/config.py` and uncomment/add an event:

```python
DEFAULT_EVENTS = [
    {
        "event_id": "6174046",  # Replace with your event ID
        "name": "Taylor Swift - Eras Tour",  # Event name
        "venue": "MetLife Stadium",  # Venue name
        "date": "2025-05-15T19:00:00Z"  # Event date/time (ISO format)
    }
]
```

### Step 5: Run the Producer

```bash
# Activate virtual environment
source venv/bin/activate

# Run producer
python producers/seatgeek_producer.py
```

You should see output like:
```
INFO - Initialized seatgeek producer (poll_interval=60s)
INFO - Starting seatgeek producer, tracking 1 events
INFO - Fetched X listings from SeatGeek for event Y
INFO - Processed X/X listings for event Y
```

### Step 6: Verify It's Working

**Check Kafka messages:**
```bash
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_prices \
  --from-beginning \
  --max-messages 5
```

**Or use Kafka UI:**
- Open http://localhost:8080
- Go to Topics → raw_prices
- Click "Messages" tab

## 🐛 Troubleshooting

### "SEATGEEK_API_KEY not found"
- Make sure `.env` file exists and contains your API key
- Check that you're running from project root

### "No events configured"
- Add events to `DEFAULT_EVENTS` in `producers/config.py`

### "No listings found"
- Verify event ID is correct
- Check if event has tickets available on SeatGeek
- Some events may not have listings yet

### "Connection refused" to Kafka
```bash
# Check services
docker-compose ps

# Restart if needed
docker-compose restart kafka
```

## 📊 Current System Status

- **Infrastructure**: ✅ Running
- **Database**: ✅ Initialized
- **Kafka Topics**: ✅ Created
- **Dependencies**: ✅ Installed
- **API Key**: ⏳ Needs to be added
- **Test Event**: ⏳ Needs to be configured
- **Producer**: ⏳ Ready to test

## 🎯 Quick Test Command

Once you have your API key and event configured:

```bash
source venv/bin/activate && python producers/seatgeek_producer.py
```

Press Ctrl+C to stop the producer.

