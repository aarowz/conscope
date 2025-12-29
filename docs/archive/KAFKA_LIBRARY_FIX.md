# Kafka Library Compatibility Fix

## Issue

`kafka-python==2.0.2` has compatibility issues with Python 3.12, causing:
```
ModuleNotFoundError: No module named 'kafka.vendor.six.moves'
```

## Solutions

### Option 1: Use Python 3.10 or 3.11 (Recommended)

```bash
# Install Python 3.11 (if not already installed)
brew install python@3.11

# Create new venv with Python 3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test
python -c "from kafka import KafkaProducer; print('✅ Works!')"
```

### Option 2: Use confluent-kafka (Alternative)

`confluent-kafka` is more actively maintained and works with Python 3.12:

```bash
pip uninstall kafka-python
pip install confluent-kafka==2.3.0
```

Then update `producers/base_producer.py`:

```python
# Change from:
from kafka import KafkaProducer
from kafka.errors import KafkaError

# To:
from confluent_kafka import Producer as KafkaProducer
from confluent_kafka import KafkaError
```

And update producer initialization:

```python
self.producer = KafkaProducer({
    'bootstrap.servers': kafka_broker,
    'compression.type': 'snappy',
})
```

### Option 3: Fix kafka-python (Workaround)

Try installing missing dependencies:

```bash
pip install six
pip install --force-reinstall kafka-python==2.0.2
```

If that doesn't work, try an older version:

```bash
pip install kafka-python==1.4.7
```

## Recommended Approach

For now, **use Python 3.11** (Option 1) as it's the most reliable. Once you have everything working, you can consider migrating to `confluent-kafka` for better Python 3.12 support.

## Verify Fix

```bash
source venv/bin/activate
python -c "from kafka import KafkaProducer; print('✅ Kafka library works!')"
```

If you see "✅ Kafka library works!", you're good to go!

