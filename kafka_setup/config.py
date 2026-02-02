"""
Kafka topic configurations for ConScope.
"""

from kafka import KafkaProducer


def get_optimal_compression_type():
    """
    Returns the best available compression type for Kafka producers.
    Tries snappy first (faster, lower latency), falls back to gzip if unavailable.
    
    kafka-python validates compression codec availability during producer initialization
    before any network calls, so we can safely test without connecting to Kafka.
    
    Returns:
        str: 'snappy' if available, 'gzip' otherwise
    """
    try:
        # Try to create a minimal producer with snappy to check codec availability
        # kafka-python checks codec availability in __init__ before connecting to brokers
        test_producer = KafkaProducer(
            bootstrap_servers=['127.0.0.1:9092'],
            compression_type='snappy'
        )
        test_producer.close()
        return 'snappy'
    except AssertionError as e:
        # Snappy libraries not available - kafka-python raises AssertionError
        # with message like "Libraries for snappy compression codec not found"
        if 'snappy' in str(e).lower() or 'compression codec' in str(e).lower():
            return 'gzip'
        # Re-raise if it's a different AssertionError
        raise
    except Exception:
        # Any other exception (e.g., connection refused) - codec validation passed,
        # so snappy is available. Return snappy.
        return 'snappy'


KAFKA_TOPICS = {
    "raw_prices": {
        "partitions": 4,  # One per source (SeatGeek, TM, StubHub, Vivid)
        "replication_factor": 1,  # Single broker for dev (increase for prod)
        "cleanup_policy": "delete",
        "retention_ms": 604800000,  # 7 days (604800000 ms)
        "compression_type": "gzip"
    },
    "processed_prices": {
        "partitions": 3,
        "replication_factor": 1,
        "cleanup_policy": "delete",
        "retention_ms": 2592000000,  # 30 days
        "compression_type": "gzip"
    },
    "price_alerts": {
        "partitions": 2,
        "replication_factor": 1,
        "cleanup_policy": "delete",
        "retention_ms": 86400000,  # 1 day
        "compression_type": "gzip"
    },
    "system_metrics": {
        "partitions": 1,
        "replication_factor": 1,
        "cleanup_policy": "compact",  # Keep latest only
        "retention_ms": 604800000
    }
}

