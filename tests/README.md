# Tests

This directory contains test scripts for the ConScope pipeline.

## Test Scripts

- `test_mock_producer.py` - Test mock producer in isolation
- `test_storage_consumer.py` - Test storage consumer
- `test_price_processor.py` - Test price change detection
- `test_complete_pipeline.py` - End-to-end pipeline test (runs until Ctrl+C)
- `test_pipeline_quick.py` - Quick 30-second pipeline test

## Running Tests

### Quick Test (Recommended)
```bash
python tests/test_pipeline_quick.py
```

### Full Pipeline Test
```bash
python tests/test_complete_pipeline.py
# Press Ctrl+C to stop
```

### Individual Component Tests
```bash
python tests/test_mock_producer.py
python tests/test_storage_consumer.py
python tests/test_price_processor.py
```

## Prerequisites

Before running tests, ensure:
1. Infrastructure is running: `docker-compose up -d`
2. Database is initialized: `python scripts/init_db.py`
3. Kafka topics are created: `python kafka_setup/create_topics.py`

See `docs/guides/TEST_PIPELINE.md` for detailed testing instructions.

