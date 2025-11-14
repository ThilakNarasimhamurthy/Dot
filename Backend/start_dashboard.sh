#!/bin/bash
# Start script for Smart City Dashboard

echo "🏙️  Smart City Dashboard"
echo "========================"
echo ""
echo "Starting API server..."
echo ""

# Check if API server is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  API server is already running on port 8000"
else
    echo "Starting API server in background..."
    cd "$(dirname "$0")"
    python3 -m app.main > /dev/null 2>&1 &
    API_PID=$!
    echo "API server started (PID: $API_PID)"
    echo "Waiting for server to be ready..."
    sleep 5
fi

echo ""
echo "✅ Dashboard is ready!"
echo ""
echo "📊 Open dashboard in your browser:"
echo "   file://$(pwd)/dashboard.html"
echo ""
echo "Or open:"
echo "   http://localhost:8000 (API endpoints)"
echo ""
echo "Press Ctrl+C to stop the API server"
echo ""

# Open dashboard in default browser
if command -v open > /dev/null; then
    open dashboard.html
elif command -v xdg-open > /dev/null; then
    xdg-open dashboard.html
fi

# Wait for user to stop
wait $API_PID 2>/dev/null || echo "API server stopped"

