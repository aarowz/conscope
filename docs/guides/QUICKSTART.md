# ConScope Quick Start Guide

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- API keys for ticket sources (SeatGeek, Ticketmaster)

## Step 1: Set Up Environment

```bash
# Clone or navigate to the project
cd conscope

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# - SEATGEEK_API_KEY: Get from https://platform.seatgeek.com/
# - TICKETMASTER_API_KEY: Get from https://developer.ticketmaster.com/
# - DISCORD_WEBHOOK_URL: Create at https://discord.com/developers/applications
```

## Step 2: Start Infrastructure

```bash
# Start Kafka, Zookeeper, PostgreSQL, and Kafka UI
docker-compose up -d

# Verify services are running
docker-compose ps

# You should see:
# - conscope-zookeeper (port 2181)
# - conscope-kafka (port 9092)
# - conscope-postgres (port 5432)
# - conscope-kafka-ui (port 8080)
```

## Step 3: Initialize Database

```bash
# Create database schema
python scripts/init_db.py

# This creates all necessary tables:
# - events
# - price_history
# - alerts
# - alert_triggers
# - system_metrics
```

## Step 4: Create Kafka Topics

```bash
# Create Kafka topics
python kafka_setup/create_topics.py

# This creates:
# - raw_prices (4 partitions)
# - processed_prices (3 partitions)
# - price_alerts (2 partitions)
# - system_metrics (1 partition)
```

## Step 5: Verify Setup

```bash
# Check Kafka topics
docker exec -it conscope-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check PostgreSQL connection
docker exec -it conscope-postgres psql -U postgres -d conscope -c "SELECT COUNT(*) FROM events;"

# Access Kafka UI (optional)
# Open http://localhost:8080 in your browser
```

## Next Steps

1. **Build your first producer** (`producers/seatgeek_producer.py`)
2. **Build storage consumer** (`consumers/storage_consumer.py`)
3. **Build price processor** (`processors/price_processor.py`)
4. **Build alert consumer** (`consumers/alert_consumer.py`)
5. **Build dashboard** (`dashboard/app.py`)

## Troubleshooting

### Kafka not starting
```bash
# Check logs
docker-compose logs kafka

# Restart services
docker-compose restart kafka zookeeper
```

### PostgreSQL connection errors
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d postgres
python scripts/init_db.py
```

### Port conflicts
If ports 2181, 9092, 5432, or 8080 are already in use:
1. Stop conflicting services, or
2. Modify ports in `docker-compose.yml`

## Development Workflow

```bash
# Terminal 1: Infrastructure (already running)
docker-compose up -d

# Terminal 2: Producer
python producers/seatgeek_producer.py

# Terminal 3: Processor
python processors/price_processor.py

# Terminal 4: Storage Consumer
python consumers/storage_consumer.py

# Terminal 5: Alert Consumer
python consumers/alert_consumer.py

# Terminal 6: Dashboard
streamlit run dashboard/app.py
```

## Useful Commands

```bash
# View Kafka messages (debugging)
docker exec -it conscope-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_prices \
  --from-beginning

# Send test message to Kafka
docker exec -it conscope-kafka kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic raw_prices

# Query database
docker exec -it conscope-postgres psql -U postgres -d conscope

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Architecture Overview

```
┌─────────────┐
│  Producers  │ → Kafka (raw_prices)
└─────────────┘
       ↓
┌─────────────┐
│ Processors  │ → Kafka (processed_prices, price_alerts)
└─────────────┘
       ↓
┌─────────────┐
│  Consumers  │ → PostgreSQL, Discord, Dashboard
└─────────────┘
```

For detailed architecture, see README.md.

