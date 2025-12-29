# Complete Pipeline Test Guide

## Prerequisites

✅ Infrastructure running: `docker-compose ps`
✅ Database initialized: `python scripts/init_db.py`
✅ Kafka topics created: `python kafka_setup/create_topics.py`

## Option 1: Test All Components Together (Recommended)

Run the automated test script:

```bash
source venv/bin/activate
python tests/test_complete_pipeline.py
```

This will:
- Start all 4 components in parallel
- Generate price events
- Process and detect price changes
- Send alerts

**Let it run for 60-90 seconds, then press Ctrl+C to stop.**

## Option 2: Test Components Individually (Step-by-Step)

### Step 1: Reset Kafka Consumer Groups (Fresh Start)

```bash
# Reset storage consumer to read from beginning
docker exec conscope-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group storage_consumer \
  --reset-offsets \
  --to-earliest \
  --topic raw_prices \
  --execute

# Reset price processor to read from beginning (for testing)
docker exec conscope-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group price_processor \
  --reset-offsets \
  --to-earliest \
  --topic raw_prices \
  --execute
```

### Step 2: Start Storage Consumer

**Terminal 1:**
```bash
source venv/bin/activate
python -m consumers.storage_consumer
```

Expected output:
- "Storage consumer initialized"
- "Stored price for event..."
- Messages being processed

### Step 3: Start Price Processor

**Terminal 2:**
```bash
source venv/bin/activate
python -m processors.price_processor
```

Expected output:
- "Price processor initialized"
- "New listing: ... at $X.XX"
- "Price change: ... | $old → $new (+X%)"
- "🚨 PRICE DROP ALERT: ..." (when prices drop)

### Step 4: Start Alert Consumer

**Terminal 3:**
```bash
source venv/bin/activate
python -m consumers.alert_consumer
```

Expected output:
- "Alert consumer initialized"
- "Discord notification sent for..." (if webhook configured)
- "Alert stored in database"

### Step 5: Start Mock Producer

**Terminal 4:**
```bash
source venv/bin/activate
python -m producers.mock_producer
```

Expected output:
- "Mock producer initialized"
- "Fetched X listings from mock API"
- "Published X price events"

**Watch all terminals** - you should see:
1. Producer generating events
2. Storage consumer storing them
3. Price processor detecting changes
4. Alert consumer sending notifications

### Step 6: View Dashboard

**Terminal 5:**
```bash
source venv/bin/activate
streamlit run dashboard/app.py
```

Open http://localhost:8501 to see:
- Price statistics
- Price history charts
- Recent alerts

## Verification Commands

### Check Database

```bash
# Count events
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) as total_events FROM events;"

# Count price history entries
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) as total_prices FROM price_history;"

# Count price drop alerts
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) as total_alerts FROM price_drop_alerts;"

# View recent alerts
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT event_name, old_price, new_price, drop_percent, alert_timestamp \
   FROM price_drop_alerts a \
   JOIN events e ON a.event_id = e.event_id \
   ORDER BY alert_timestamp DESC \
   LIMIT 10;"
```

### Check Kafka Topics

```bash
# View messages in raw_prices
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_prices \
  --from-beginning \
  --max-messages 5

# View price alerts
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic price_alerts \
  --from-beginning \
  --max-messages 5
```

### Check Kafka UI

Open http://localhost:8080 in your browser:
- View topics and messages
- Monitor consumer groups
- Check topic offsets

## Expected Results

After running for 60-90 seconds:

✅ **Events**: 4 events (from TEST_EVENTS)
✅ **Price History**: 100+ price entries
✅ **Price Drops**: 5-15 price drop alerts
✅ **Database**: All data stored correctly
✅ **Dashboard**: Shows charts and statistics

## Troubleshooting

### No Price Drops Detected

The price processor starts from `latest` offset by default. If storage consumer already processed messages, the processor won't see them.

**Solution**: Reset the price processor consumer group (see Step 1 above).

### Storage Consumer Not Processing

Check if consumer group has committed offsets:
```bash
docker exec conscope-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group storage_consumer \
  --describe
```

Reset if needed (see Step 1).

### Dashboard Shows No Data

- Ensure storage consumer has processed messages
- Check database connection
- Verify events exist: `SELECT * FROM events LIMIT 5;`

### Alert Consumer Not Sending Discord Notifications

- Check `.env` file has `DISCORD_WEBHOOK_URL` set
- Test webhook URL manually:
  ```bash
  curl -X POST YOUR_WEBHOOK_URL \
    -H "Content-Type: application/json" \
    -d '{"content": "Test message"}'
  ```

## Success Criteria

✅ All components start without errors
✅ Mock producer generates price events
✅ Storage consumer stores events and prices
✅ Price processor detects price changes
✅ Price drop alerts are created
✅ Alert consumer sends notifications (if configured)
✅ Dashboard displays data
✅ Database contains all records

---

**Ready to test!** Start with Option 1 (automated test) or Option 2 (step-by-step).

