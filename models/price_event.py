"""
PriceEvent data model for ConScope.

This module defines the PriceEvent dataclass that represents a ticket price
update from any source (SeatGeek, Ticketmaster, etc.).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json


@dataclass
class PriceEvent:
    """
    Represents a ticket price event from a ticket source.
    
    This is the standard format for all price data flowing through Kafka.
    """
    # Event identification
    event_id: str              # e.g., "taylor_swift_metlife_2025"
    event_name: str            # e.g., "Taylor Swift - Eras Tour"
    venue: str                 # e.g., "MetLife Stadium"
    event_date: datetime       # When the concert happens
    
    # Ticket details
    source: str                # "seatgeek", "ticketmaster", "stubhub", "vivid"
    section: str               # e.g., "Floor 2", "Section 101"
    row: str                   # e.g., "15", "A"
    seat: str                 # e.g., "8", "12-13"
    
    # Price information
    price: float               # Current price in USD
    fees: Optional[float] = None      # Service fees (if available)
    total_price: float         # Price + fees
    
    # Metadata
    timestamp: datetime        # When price was scraped
    listing_id: str            # Source-specific listing ID
    listing_url: str           # Link to listing
    quantity: int = 1         # Number of tickets (usually 1 or 2)
    
    # Optional fields
    delivery_method: Optional[str] = None  # "mobile", "physical", "instant"
    seller_notes: Optional[str] = None      # Any special notes
    
    def to_dict(self) -> dict:
        """Convert PriceEvent to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "venue": self.venue,
            "event_date": self.event_date.isoformat() if isinstance(self.event_date, datetime) else self.event_date,
            "source": self.source,
            "section": self.section,
            "row": self.row,
            "seat": self.seat,
            "price": self.price,
            "fees": self.fees,
            "total_price": self.total_price,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "listing_id": self.listing_id,
            "listing_url": self.listing_url,
            "quantity": self.quantity,
            "delivery_method": self.delivery_method,
            "seller_notes": self.seller_notes
        }
    
    def to_json(self) -> str:
        """Convert PriceEvent to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PriceEvent':
        """Create PriceEvent from dictionary."""
        # Handle datetime strings
        if isinstance(data.get('event_date'), str):
            data['event_date'] = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        return cls(**data)

