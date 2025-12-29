#!/bin/bash
# ConScope Complete Pipeline Runner
# This script helps you run all components for testing

echo "🎫 ConScope Pipeline Test"
echo "========================"
echo ""
echo "This script will help you test the complete pipeline."
echo ""
echo "Choose an option:"
echo "1. Run automated test (all components together)"
echo "2. Get step-by-step instructions"
echo "3. Verify setup only"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting automated test..."
        echo "   This will run all components for 60 seconds"
        echo "   Press Ctrl+C to stop early"
        echo ""
        source venv/bin/activate
        python tests/test_complete_pipeline.py
        ;;
    2)
        echo ""
        echo "📋 Step-by-Step Instructions:"
        echo ""
        echo "Open 5 terminals and run these commands:"
        echo ""
        echo "Terminal 1 (Storage Consumer):"
        echo "  source venv/bin/activate"
        echo "  python -m consumers.storage_consumer"
        echo ""
        echo "Terminal 2 (Price Processor):"
        echo "  source venv/bin/activate"
        echo "  python -m processors.price_processor"
        echo ""
        echo "Terminal 3 (Alert Consumer):"
        echo "  source venv/bin/activate"
        echo "  python -m consumers.alert_consumer"
        echo ""
        echo "Terminal 4 (Mock Producer):"
        echo "  source venv/bin/activate"
        echo "  python -m producers.mock_producer"
        echo ""
        echo "Terminal 5 (Dashboard):"
        echo "  source venv/bin/activate"
        echo "  streamlit run dashboard/app.py"
        echo ""
        echo "Then open http://localhost:8501 in your browser"
        ;;
    3)
        echo ""
        echo "🔍 Verifying setup..."
        echo ""
        
        # Check Docker
        echo "Checking Docker services..."
        docker-compose ps | grep -q "Up" && echo "✅ Docker services running" || echo "❌ Docker services not running"
        
        # Check database
        echo "Checking database..."
        docker exec conscope-postgres psql -U postgres -d conscope -c "SELECT 1" > /dev/null 2>&1 && echo "✅ Database connected" || echo "❌ Database not connected"
        
        # Check Kafka topics
        echo "Checking Kafka topics..."
        topics=$(docker exec conscope-kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | wc -l)
        if [ "$topics" -gt 0 ]; then
            echo "✅ Kafka topics exist ($topics topics)"
        else
            echo "❌ No Kafka topics found"
        fi
        
        # Check Python environment
        echo "Checking Python environment..."
        source venv/bin/activate
        python -c "import kafka, psycopg2, streamlit, plotly" > /dev/null 2>&1 && echo "✅ Python dependencies installed" || echo "❌ Missing Python dependencies"
        
        echo ""
        echo "✅ Verification complete!"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

