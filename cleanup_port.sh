#!/bin/bash

echo "🧹 Cleaning up DataPrime Assistant processes..."
echo "============================================="

# Kill any processes using port 8000
echo "🔍 Looking for processes on port 8000..."
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "⚠️  Found processes using port 8000, killing them..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    echo "✅ Killed processes on port 8000"
else
    echo "✅ No processes found on port 8000"
fi

# Kill any Python app processes
echo "🔍 Looking for DataPrime Assistant processes..."
if pgrep -f "python.*minimal_dataprime_app" >/dev/null 2>&1; then
    echo "⚠️  Found DataPrime Assistant processes, killing them..."
    pkill -f "python.*minimal_dataprime_app" 2>/dev/null
    echo "✅ Killed DataPrime Assistant processes"
else
    echo "✅ No DataPrime Assistant processes found"
fi

echo ""
echo "🎯 Cleanup complete! Port 8000 should now be available."
echo "You can now run: ./start_app.sh" 