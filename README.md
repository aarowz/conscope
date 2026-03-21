# ConScope

Real-time event ticket price monitoring system using Kafka to track concert prices across multiple sources and alert users when prices drop.

## Features

- ✅ **Real-Time Price Monitoring**: Track ticket prices from multiple sources (SeatGeek, Ticketmaster, Mock)
- ✅ **Price Change Detection**: Automatically detect price drops and increases in real-time
- ✅ **Price Drop Alerts**: Get notified via Discord webhooks when prices drop
- ✅ **Price History Tracking**: Store all price updates in PostgreSQL for historical analysis
- ✅ **Interactive Dashboard**: Visualize price trends, alerts, and statistics with Streamlit
- ✅ **Distributed Architecture**: Event-driven system built with Apache Kafka for scalability
- ✅ **Mock Producer**: Test the system without API keys using realistic mock data

## Tech Stack

- **Message Queue**: Apache Kafka + Zookeeper
- **Backend**: Python, Kafka Streams
- **Storage**: PostgreSQL
- **Dashboard**: Streamlit
- **Deployment**: Docker Compose

## Architecture

```
API Producers → Kafka Topics → Stream Processors → Consumers
                                                   ↓
                                           PostgreSQL
                                           Alert Service
                                           Dashboard
```

## Getting Started

### Prerequisites

- Python 3.10+ (3.12+ not recommended due to kafka-python compatibility)
- Docker & Docker Compose
- API keys for ticket sources (optional - mock producer works without keys)

### Installation

```bash
# Clone repository
git clone https://github.com/aarowz/conscope.git
cd conscope

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (Command Prompt):
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your API keys to .env
```

### Running the System

#### Quick Start (Using Mock Producer)

For testing without API keys, use the one-command launcher:

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Initialize database
python scripts/init_db.py

# 3. Create Kafka topics
python kafka_setup/create_topics.py

# 4. Start everything (single terminal)
python scripts/run_all.py
```

This starts storage consumer, processor, alert consumer, mock producer, and dashboard.
Open `http://localhost:8501` to view the app.

Press **Ctrl+C** to stop all components.

#### Optional: Backend only (dashboard separate)

```bash
# Start backend components only
python scripts/run_all.py --no-dashboard

# In another terminal, start dashboard
streamlit run dashboard/app.py
```

#### Production Setup (With Real API Keys)

```bash
# 1. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# 2. Start infrastructure
docker-compose up -d

# 3. Initialize database
python scripts/init_db.py

# 4. Create Kafka topics
python kafka_setup/create_topics.py

# 5. Start components (in separate terminals)
python -m producers.seatgeek_producer  # Requires SEATGEEK_API_KEY
python -m processors.price_processor
python -m consumers.storage_consumer
python -m consumers.alert_consumer
streamlit run dashboard/app.py
```

#### Automated Testing

Run the complete pipeline test:

```bash
# Test all components together for 30 seconds
python tests/test_pipeline_quick.py

# Or run full test (until Ctrl+C)
python tests/test_complete_pipeline.py
```

## Project Structure

```
conscope/
├── producers/          # API pollers that publish to Kafka
│   ├── base_producer.py      # Abstract base class for producers
│   ├── mock_producer.py      # Mock producer for testing
│   ├── seatgeek_producer.py  # SeatGeek API producer
│   └── config.py             # Producer configuration
├── processors/         # Stream processing logic
│   └── price_processor.py    # Price change detection
├── consumers/          # Kafka consumers
│   ├── storage_consumer.py   # Stores events in PostgreSQL
│   └── alert_consumer.py     # Sends Discord notifications
├── dashboard/          # Streamlit dashboard
│   └── app.py                # Main dashboard application
├── models/            # Data models
│   └── price_event.py        # PriceEvent dataclass
├── kafka_setup/       # Kafka configuration
│   ├── config.py             # Topic configurations
│   └── create_topics.py      # Topic creation script
├── scripts/           # Utility scripts
│   ├── init_db.py            # Database schema initialization
│   └── run_pipeline.sh        # Pipeline runner script
├── tests/              # Test scripts
│   ├── test_complete_pipeline.py
│   ├── test_mock_producer.py
│   ├── test_storage_consumer.py
│   ├── test_price_processor.py
│   └── test_pipeline_quick.py
├── docs/              # Documentation
│   ├── guides/               # User guides
│   └── archive/              # Historical docs
├── docker-compose.yml  # Infrastructure orchestration
├── requirements.txt    # Python dependencies
└── README.md
```

## Data Schema

### PriceEvent

```python
{
    "event_id": "concert_123",
    "event_name": "Taylor Swift Eras",
    "venue": "MetLife Stadium",
    "date": "2025-05-15T19:00:00Z",
    "source": "seatgeek",
    "section": "Floor 2",
    "row": "15",
    "seat": "8",
    "price": 245.50,
    "timestamp": "2025-01-15T14:30:00Z",
    "url": "https://seatgeek.com/..."
}
```

## System Metrics

- **Processing Capacity**: 10k+ price updates per hour
- **Alert Latency**: <60 seconds from price drop to notification
- **Data Sources**: Mock (testing), SeatGeek (production-ready), Ticketmaster (planned)
- **Concurrent Events**: Monitor multiple events simultaneously
- **Dashboard**: Real-time visualization with auto-refresh

## Testing

The system includes comprehensive test scripts in the `tests/` directory:

- `tests/test_mock_producer.py` - Test mock producer in isolation
- `tests/test_storage_consumer.py` - Test storage consumer
- `tests/test_price_processor.py` - Test price change detection
- `tests/test_complete_pipeline.py` - End-to-end pipeline test
- `tests/test_pipeline_quick.py` - Quick 30-second test

See `docs/guides/TEST_PIPELINE.md` for detailed testing instructions.

## Roadmap

### ✅ Completed (MVP)

- [x] Kafka infrastructure setup (Zookeeper, Kafka, Kafka UI)
- [x] PostgreSQL database schema and initialization
- [x] Base producer architecture with error handling
- [x] Mock producer for testing without API keys
- [x] SeatGeek producer (ready for API key)
- [x] Storage consumer with connection pooling
- [x] Price change detection processor
- [x] Price drop alert system
- [x] Discord webhook notifications
- [x] Streamlit dashboard with interactive visualizations
- [x] End-to-end pipeline testing

### 🚀 Future Enhancements

- [ ] Ticketmaster producer integration
- [ ] Email notifications (in addition to Discord)
- [ ] Price prediction ML model
- [ ] Deduplication across sources
- [ ] Optimal buy time analysis
- [ ] User alert management (web UI)
- [ ] Production deployment guide
- [ ] Kubernetes/Docker Swarm orchestration

## API Sources

- [SeatGeek API](https://platform.seatgeek.com/)
- [Ticketmaster Discovery API](https://developer.ticketmaster.com/)
- StubHub (if available)
- Vivid Seats (if available)

## Documentation

- `README.md` - Main project documentation (you are here)
- `PROJECT_COMPLETE.md` - Project completion summary and demo guide
- `docs/guides/QUICKSTART.md` - Detailed setup guide
- `docs/guides/TEST_PIPELINE.md` - Testing instructions
- `docs/guides/MOCK_PRODUCER_GUIDE.md` - Using the mock producer
- `docs/guides/PRODUCER_SETUP.md` - Setting up real API producers

## Contributing

This is a personal learning project, but feedback and suggestions are welcome! Feel free to open an issue.

## Use Cases

While built for concert tickets, the architecture is extensible to any price tracking use case:

- Real estate (Zillow, Redfin)
- Stock prices
- Retail products
- Flight prices
- Cryptocurrency

## License

MIT License - see LICENSE file for details.

## Author

Aaron Zhou - [GitHub](https://github.com/aarowz) | [LinkedIn](https://linkedin.com/in/aaron-zihan-zhou)

---

**Built with Kafka for distributed, real-time event processing.**
