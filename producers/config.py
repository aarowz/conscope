"""
Producer configuration for ConScope.

This module contains configuration for all ticket source producers,
including API endpoints, rate limits, and event tracking settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_RAW_PRICES = "raw_prices"

# Producer Settings
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

# SeatGeek API Configuration
SEATGEEK_API_KEY = os.getenv("SEATGEEK_API_KEY")
SEATGEEK_BASE_URL = "https://api.seatgeek.com/2"
SEATGEEK_RATE_LIMIT = 5000  # Requests per hour (free tier)

# Ticketmaster API Configuration
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
TICKETMASTER_BASE_URL = "https://app.ticketmaster.com/discovery/v2"
TICKETMASTER_RATE_LIMIT = 5000  # Requests per day (free tier)

# StubHub API Configuration (if available)
STUBHUB_API_KEY = os.getenv("STUBHUB_API_KEY")
STUBHUB_BASE_URL = "https://api.stubhub.com"

# Vivid Seats API Configuration (if available)
VIVID_SEATS_API_KEY = os.getenv("VIVID_SEATS_API_KEY")
VIVID_SEATS_BASE_URL = "https://api.vividseats.com"

# Default events to track (can be overridden)
# Format: {"event_id": "seatgeek_event_id", "name": "Event Name", "venue": "Venue Name", "date": "ISO datetime"}
DEFAULT_EVENTS = [
    # Example: Add your events here
    # To find event IDs, visit seatgeek.com and check the URL of an event page
    # Example: seatgeek.com/taylor-swift-eras-tour-tickets/6174046 -> event_id is 6174046
    # {
    #     "event_id": "6174046",  # SeatGeek event ID
    #     "name": "Taylor Swift - Eras Tour",
    #     "venue": "MetLife Stadium",
    #     "date": "2025-05-15T19:00:00Z"
    # }
]

