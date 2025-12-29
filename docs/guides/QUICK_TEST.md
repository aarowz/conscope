# Quick Test Guide - Complete Pipeline

## ✅ Setup Verified

All components are ready! Here's how to test:

## 🚀 Quick Test (Recommended)

### Option A: Automated Test Script

```bash
source venv/bin/activate
python tests/test_complete_pipeline.py
```

This runs all components together. Let it run for 60-90 seconds, then press Ctrl+C.

### Option B: Interactive Script

```bash
./scripts/run_pipeline.sh
```

Choose option 1 for automated test, or option 2 for step-by-step instructions.

## 📋 Manual Test (5 Terminals)

For better visibility of what each component does:

**Terminal 1 - Storage Consumer:**
```bash
source venv/bin/activate
python -m consumers.storage_consumer
```

**Terminal 2 - Price Processor:**
```bash
source venv/bin/activate
python -m processors.price_processor
```

**Terminal 3 - Alert Consumer:**
```bash
source venv/bin/activate
python -m consumers.alert_consumer
```

**Terminal 4 - Mock Producer:**
```bash
source venv/bin/activate
python -m producers.mock_producer
```

**Terminal 5 - Dashboard:**
```bash
source venv/bin/activate
streamlit run dashboard/app.py
```

Then open http://localhost:8501

## 🔍 What to Watch For

### Storage Consumer
- ✅ "Stored price for event..."
- ✅ Messages being processed
- ✅ Metrics logged every 100 messages

### Price Processor
- ✅ "New listing: ... at $X.XX"
- ✅ "Price change: Event | Section | $old → $new (+X%)"
- ✅ "🚨 PRICE DROP ALERT: ..." (when prices drop)

### Alert Consumer
- ✅ "Discord notification sent for..." (if webhook configured)
- ✅ "Alert stored in database"

### Mock Producer
- ✅ "Fetched X listings from mock API"
- ✅ "Published X price events"

### Dashboard
- ✅ Price statistics cards
- ✅ Price history chart
- ✅ Recent alerts table

## ✅ Verification

After 60-90 seconds, check:

```bash
# Count alerts
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT COUNT(*) as alerts FROM price_drop_alerts;"

# View recent alerts
docker exec conscope-postgres psql -U postgres -d conscope -c \
  "SELECT e.event_name, a.old_price, a.new_price, a.drop_percent \
   FROM price_drop_alerts a \
   JOIN events e ON a.event_id = e.event_id \
   ORDER BY a.alert_timestamp DESC \
   LIMIT 5;"
```

You should see:
- ✅ 5-15 price drop alerts
- ✅ Price changes detected
- ✅ Alerts stored in database
- ✅ Dashboard showing data

## 🎯 Success Criteria

✅ All components start without errors
✅ Mock producer generates events
✅ Storage consumer stores data
✅ Price processor detects changes
✅ Price drops trigger alerts
✅ Alert consumer processes alerts
✅ Dashboard displays data
✅ Database contains all records

---

**Ready to test!** Start with the automated script or run components manually.

