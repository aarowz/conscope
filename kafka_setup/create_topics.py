#!/usr/bin/env python3
"""
Create Kafka topics for ConScope.

This script creates all necessary Kafka topics with proper configurations.
Run this after starting Kafka with docker-compose.
"""

import os
import sys
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Topic configurations
KAFKA_TOPICS = {
    "raw_prices": {
        "num_partitions": 4,  # One per source (SeatGeek, TM, StubHub, Vivid)
        "replication_factor": 1,  # Single broker for dev
        "configs": {
            "cleanup.policy": "delete",
            "retention.ms": "604800000",  # 7 days
            "compression.type": "snappy"
        }
    },
    "processed_prices": {
        "num_partitions": 3,
        "replication_factor": 1,
        "configs": {
            "cleanup.policy": "delete",
            "retention.ms": "2592000000",  # 30 days
            "compression.type": "snappy"
        }
    },
    "price_alerts": {
        "num_partitions": 2,
        "replication_factor": 1,
        "configs": {
            "cleanup.policy": "delete",
            "retention.ms": "86400000",  # 1 day
            "compression.type": "snappy"
        }
    },
    "system_metrics": {
        "num_partitions": 1,
        "replication_factor": 1,
        "configs": {
            "cleanup.policy": "compact",  # Keep latest only
            "retention.ms": "604800000"  # 7 days
        }
    }
}

def create_topics():
    """Create all Kafka topics."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    print(f"🚀 Connecting to Kafka at {bootstrap_servers}...")
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id="conscope-topic-creator"
        )
        
        topics_to_create = []
        
        for topic_name, config in KAFKA_TOPICS.items():
            topic = NewTopic(
                name=topic_name,
                num_partitions=config["num_partitions"],
                replication_factor=config["replication_factor"],
                topic_configs=config.get("configs", {})
            )
            topics_to_create.append(topic)
        
        # Create topics
        print("\n📝 Creating topics...")
        try:
            admin_client.create_topics(new_topics=topics_to_create, validate_only=False)
            print("✅ Topics created successfully!")
        except TopicAlreadyExistsError:
            print("⚠️  Some topics already exist. Skipping...")
        
        # List existing topics
        print("\n📊 Existing topics:")
        metadata = admin_client.describe_topics()
        for topic_name in sorted(KAFKA_TOPICS.keys()):
            if topic_name in metadata:
                topic_metadata = metadata[topic_name]
                partitions = len(topic_metadata.partitions)
                print(f"   - {topic_name}: {partitions} partition(s)")
        
        admin_client.close()
        print("\n✅ Kafka topic setup complete!")
        
    except Exception as e:
        print(f"❌ Error creating topics: {e}")
        print("\n💡 Make sure Kafka is running:")
        print("   docker-compose up -d kafka")
        sys.exit(1)

def main():
    """Main function."""
    print("🚀 Initializing ConScope Kafka topics...\n")
    create_topics()

if __name__ == "__main__":
    main()

