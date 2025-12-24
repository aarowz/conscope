# ConScope

Real-time event ticket price monitoring system using Kafka to track concert prices across multiple sources and alert users when prices drop.

## Features

- **Multi-Source Price Tracking**: Monitor prices from StubHub, SeatGeek, Ticketmaster, and Vivid Seats
- **Real-Time Alerts**: Get notified within 60 seconds when prices drop below your target
- **Price History**: Track historical price trends to identify optimal buy times
- **Arbitrage Detection**: Find the same seat at different prices across platforms
- **Distributed Architecture**: Event-driven system built with Apache Kafka

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

- Python 3.10+
- Docker & Docker Compose
- API keys for ticket sources

### Installation
```bash
# Clone repository
git clone https://github.com/aarowz/conscope.git
cd conscope

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your API keys to .env
```

### Running the System
```bash
# Start Kafka, Zookeeper, and PostgreSQL
docker-compose up -d

# Initialize database schema
python scripts/init_db.py

# Start producers (in separate terminals)
python producers/seatgeek_producer.py
python producers/ticketmaster_producer.py

# Start processors
python processors/price_processor.py

# Start consumers
python consumers/storage_consumer.py
python consumers/alert_consumer.py

# Run dashboard
streamlit run dashboard/app.py
```

Navigate to `http://localhost:8501` to view the dashboard.

## Project Structure
```
conscope/
├── producers/          # API pollers that publish to Kafka
├── processors/         # Kafka Streams processing logic
├── consumers/          # Alert and storage consumers
├── dashboard/          # Streamlit dashboard
├── models/            # Data models and database schema
├── kafka_setup/       # Topic creation and configuration
├── docker-compose.yml
├── requirements.txt
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

## Metrics

- Process **10k+ price updates per hour**
- Alert latency: **<60 seconds**
- Track prices across **4 ticket sources**
- Monitor **multiple concurrent events**

## Roadmap

- [x] Kafka infrastructure setup
- [x] SeatGeek producer
- [x] Ticketmaster producer
- [x] Price change detection
- [x] PostgreSQL storage
- [ ] Email/Discord notifications
- [ ] Price prediction ML model
- [ ] Deduplication across sources
- [ ] Optimal buy time analysis
- [ ] Production deployment

## API Sources

- [SeatGeek API](https://platform.seatgeek.com/)
- [Ticketmaster Discovery API](https://developer.ticketmaster.com/)
- StubHub (if available)
- Vivid Seats (if available)

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
