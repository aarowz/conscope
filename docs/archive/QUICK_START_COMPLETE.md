# ConScope - Complete System Guide

## 🎉 System Status: MVP Complete!

All core components have been built and are ready for testing.

## 📦 What's Been Built

### 1. **Price Processor** (`processors/price_processor.py`)
- ✅ Reads from `raw_prices` Kafka topic
- ✅ Maintains in-memory cache of last seen prices
- ✅ Detects price changes (drops and increases)
- ✅ Publishes all processed events to `processed_prices` topic
- ✅ Publishes price drops to `price_alerts` topic
- ✅ Comprehensive metrics tracking

### 2. **Alert Consumer** (`consumers/alert_consumer.py`)
- ✅ Reads from `price_alerts` Kafka topic
- ✅ Sends Discord webhook notifications with formatted embeds
- ✅ Stores alerts in PostgreSQL `price_drop_alerts` table
- ✅ Error handling and metrics tracking

### 3. **Dashboard** (`dashboard/app.py`)
- ✅ Real-time price statistics (total listings, avg/min/max prices)
- ✅ Interactive price history charts (Plotly)
- ✅ Recent price drop alerts table
- ✅ Event filtering and time range selection
- ✅ Auto-refresh capability
- ✅ Price distribution visualizations

### 4. **Database Schema Update**
- ✅ Added `price_drop_alerts` table to store detected price drops
- ✅ Proper indexes for performance

## 🚀 Complete Setup Instructions

### Step 1: Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Step 2: Initialize Database

```bash
# Create/update database schema (includes new price_drop_alerts table)
python scripts/init_db.py

# Verify tables
docker exec conscope-postgres psql -U postgres -d conscope -c "\dt"
```

### Step 3: Create Kafka Topics

```bash
# Create all Kafka topics
python kafka_setup/create_topics.py

# Verify topics
docker exec conscope-kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Step 4: Run the Complete Pipeline

Open **6 terminals** (or use tmux/screen):

**Terminal 1: Mock Producer**
```bash
source venv/bin/activate
python -m producers.mock_producer
```

**Terminal 2: Storage Consumer**
```bash
source venv/bin/activate
python -m consumers.storage_consumer
```

**Terminal 3: Price Processor**
```bash
source venv/bin/activate
python -m processors.price_processor
```

**Terminal 4: Alert Consumer** (Optional - needs Discord webhook)
```bash
source venv/bin/activate
python -m consumers.alert_consumer
```

**Terminal 5: Dashboard**
```bash
source venv/bin/activate
streamlit run dashboard/app.py
```

**Terminal 6: Monitor Kafka** (Optional)
```bash
# View messages in raw_prices topic
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_prices \
  --from-beginning

# View price alerts
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic price_alerts \
  --from-beginning
```

## 🔧 Configuration

### Discord Webhook Setup (Optional)

1. Create a Discord webhook:
   - Go to your Discord server settings
   - Integrations → Webhooks → New Webhook
   - Copy the webhook URL

2. Add to `.env`:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url
   ```

3. Restart alert consumer after adding webhook

### Environment Variables

Make sure your `.env` file has:
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=conscope
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
DISCORD_WEBHOOK_URL=your_webhook_url  # Optional
```

## 📊 What to Expect

### Mock Producer
- Generates 2-5 listings per event every 5 seconds
- Simulates price changes (drops, increases, stable)
- Publishes to `raw_prices` topic

### Storage Consumer
- Processes messages from `raw_prices`
- Creates events in `events` table
- Stores prices in `price_history` table
- Logs: "Stored price for event..."

### Price Processor
- Processes messages from `raw_prices`
- Detects price changes
- Logs: "Price change: Event | Section | $old → $new (+X%)"
- Logs: "🚨 PRICE DROP ALERT: ..." when prices drop
- Publishes to `processed_prices` and `price_alerts`

### Alert Consumer
- Processes alerts from `price_alerts`
- Sends Discord notifications (if webhook configured)
- Stores alerts in `price_drop_alerts` table
- Logs: "Discord notification sent for..."

### Dashboard
- Open http://localhost:8501
- View real-time statistics
- See price history charts
- View recent alerts
- Filter by event and time range

## 🧪 Testing the System

### Test Price Drop Detection

1. Let the mock producer run for 30-60 seconds
2. Watch the price processor logs for price drop alerts
3. Check the dashboard for alerts
4. Verify Discord notifications (if configured)

### Verify Data Flow

```bash
# Check events in database
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) FROM events;"

# Check price history
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) FROM price_history;"

# Check price drop alerts
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) FROM price_drop_alerts;"
```

## 🐛 Troubleshooting

### Price Processor Not Detecting Changes
- Make sure mock producer is running and generating messages
- Check that storage consumer has processed some messages first (to populate initial prices)
- Price processor starts from `latest` offset, so it only sees new messages

### No Alerts in Dashboard
- Ensure price processor is running
- Check that price drops have occurred (mock producer simulates this)
- Verify `price_drop_alerts` table exists: `python scripts/init_db.py`

### Discord Notifications Not Sending
- Verify `DISCORD_WEBHOOK_URL` is set in `.env`
- Test webhook URL manually with curl
- Check alert consumer logs for errors

### Dashboard Shows No Data
- Ensure storage consumer has processed messages
- Check database connection in dashboard logs
- Verify events exist: `SELECT * FROM events LIMIT 5;`

## 📈 Next Steps

1. **Test with Real API**: Replace mock producer with SeatGeek producer (once API key is approved)
2. **Add More Producers**: Ticketmaster, StubHub, etc.
3. **Enhance Dashboard**: Add more visualizations, filters, export features
4. **Add User Alerts**: Allow users to set custom price thresholds
5. **Production Deployment**: Deploy to cloud infrastructure

## 🎯 System Architecture

```
┌─────────────┐
│   Producer  │ → Kafka (raw_prices)
└─────────────┘
       ↓
┌─────────────┐     ┌─────────────┐
│   Storage   │     │   Price     │
│  Consumer   │     │  Processor  │
└─────────────┘     └─────────────┘
       ↓                   ↓
  PostgreSQL        Kafka (processed_prices)
                           ↓
                    Kafka (price_alerts)
                           ↓
                    ┌─────────────┐
                    │   Alert     │
                    │  Consumer   │
                    └─────────────┘
                           ↓
                    Discord + PostgreSQL
                           ↓
                    ┌─────────────┐
                    │  Dashboard  │
                    └─────────────┘
```

## ✅ MVP Checklist

- [x] Infrastructure (Docker Compose)
- [x] Database schema
- [x] Kafka topics
- [x] Mock producer
- [x] Storage consumer
- [x] Price processor
- [x] Alert consumer
- [x] Dashboard
- [ ] Real API integration (pending API key)
- [ ] Production deployment

---

**Status**: All MVP components complete! Ready for testing and integration with real APIs.

