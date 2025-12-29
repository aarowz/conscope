"""
Kafka topic configurations for ConScope.
"""

KAFKA_TOPICS = {
    "raw_prices": {
        "partitions": 4,  # One per source (SeatGeek, TM, StubHub, Vivid)
        "replication_factor": 1,  # Single broker for dev (increase for prod)
        "cleanup_policy": "delete",
        "retention_ms": 604800000,  # 7 days (604800000 ms)
        "compression_type": "snappy"
    },
    "processed_prices": {
        "partitions": 3,
        "replication_factor": 1,
        "cleanup_policy": "delete",
        "retention_ms": 2592000000,  # 30 days
        "compression_type": "snappy"
    },
    "price_alerts": {
        "partitions": 2,
        "replication_factor": 1,
        "cleanup_policy": "delete",
        "retention_ms": 86400000,  # 1 day
        "compression_type": "snappy"
    },
    "system_metrics": {
        "partitions": 1,
        "replication_factor": 1,
        "cleanup_policy": "compact",  # Keep latest only
        "retention_ms": 604800000
    }
}

