#!/usr/bin/env python3
"""
Initialize PostgreSQL database schema for ConScope.

This script creates all necessary tables for events, price history, alerts, and metrics.
Run this after starting PostgreSQL with docker-compose.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_config():
    """Get database configuration from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DB", "conscope"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "password"),
    }

def create_schema(conn):
    """Create all database tables."""
    cursor = conn.cursor()
    
    # Events table (concerts being tracked)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(255) UNIQUE NOT NULL,
            event_name VARCHAR(255) NOT NULL,
            venue VARCHAR(255) NOT NULL,
            event_date TIMESTAMP NOT NULL,
            city VARCHAR(100),
            state VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW(),
            last_updated TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_event_date ON events(event_date);
    """)
    
    # Price history (all price updates)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(255) NOT NULL,
            source VARCHAR(50) NOT NULL,
            section VARCHAR(50),
            row VARCHAR(10),
            seat VARCHAR(10),
            price DECIMAL(10,2) NOT NULL,
            fees DECIMAL(10,2),
            total_price DECIMAL(10,2) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            listing_id VARCHAR(255),
            listing_url TEXT,
            quantity INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_event_id ON price_history(event_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_source ON price_history(source);
    """)
    
    # User alerts (price thresholds to monitor)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) DEFAULT 'default_user',
            event_id VARCHAR(255) NOT NULL,
            target_price DECIMAL(10,2) NOT NULL,
            section VARCHAR(50),
            max_row INT,
            notification_method VARCHAR(50) DEFAULT 'discord',
            notification_target VARCHAR(255),
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            last_triggered TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_event_id ON alerts(event_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);
    """)
    
    # Alert triggers (history of when alerts fired)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_triggers (
            id SERIAL PRIMARY KEY,
            alert_id INT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            source VARCHAR(50) NOT NULL,
            section VARCHAR(50),
            row VARCHAR(10),
            seat VARCHAR(10),
            listing_url TEXT,
            triggered_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_triggers_alert_id ON alert_triggers(alert_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_triggers_triggered_at ON alert_triggers(triggered_at);
    """)
    
    # Price drop alerts (detected price drops from processor)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_drop_alerts (
            alert_id SERIAL PRIMARY KEY,
            event_id VARCHAR(255) NOT NULL,
            alert_type VARCHAR(50) DEFAULT 'price_drop',
            alert_timestamp TIMESTAMP NOT NULL,
            old_price DECIMAL(10,2) NOT NULL,
            new_price DECIMAL(10,2) NOT NULL,
            drop_amount DECIMAL(10,2) NOT NULL,
            drop_percent DECIMAL(5,2) NOT NULL,
            section VARCHAR(50),
            row VARCHAR(10),
            seat VARCHAR(10),
            source VARCHAR(50) NOT NULL,
            listing_id VARCHAR(255),
            listing_url TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_drop_alerts_event_id ON price_drop_alerts(event_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_drop_alerts_timestamp ON price_drop_alerts(alert_timestamp);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_drop_alerts_listing_id ON price_drop_alerts(listing_id);
    """)
    
    # System metrics (for monitoring)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id SERIAL PRIMARY KEY,
            metric_name VARCHAR(100) NOT NULL,
            metric_value DECIMAL(15,2) NOT NULL,
            timestamp TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
    """)
    
    conn.commit()
    cursor.close()
    print("✅ Database schema created successfully!")

def main():
    """Main function to initialize database."""
    print("🚀 Initializing ConScope database...")
    
    db_config = get_db_config()
    
    try:
        # Connect to PostgreSQL
        print(f"📡 Connecting to PostgreSQL at {db_config['host']}:{db_config['port']}...")
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create schema
        create_schema(conn)
        
        # Verify tables were created
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print("\n📊 Created tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database initialization complete!")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Error connecting to database: {e}")
        print("\n💡 Make sure PostgreSQL is running:")
        print("   docker-compose up -d postgres")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

