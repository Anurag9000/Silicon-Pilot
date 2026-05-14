#!/bin/bash
# start_silicon_pilot.sh - One-click runner for Silicon-Pilot
# Detects OS, starts the server, and opens the browser.

set -e

# 1. Detect OS
OS_NAME=$(uname -s | tr '[:upper:]' '[:lower:]')
echo "Detected OS: $OS_NAME"

# Trap Ctrl+C (SIGINT) to clean up
cleanup() {
    echo -e "\n🛑 Stopping Silicon-Pilot..."
    echo "🧹 Freeing GPU VRAM (unloading LLM)..."
    curl -s -X POST http://localhost:11434/api/generate -d '{"model": "qwen2.5:7b", "keep_alive": 0}' > /dev/null || true
    echo "🛑 Killing Uvicorn backend..."
    if [[ -n "$SERVER_PID" ]]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "🧹 Initial GPU check: Unloading any stuck LLM models to free VRAM..."
curl -s -X POST http://localhost:11434/api/generate -d '{"model": "qwen2.5:7b", "keep_alive": 0}' > /dev/null || true

# 2. Check dependencies
if ! command -v python3 &> /dev/null; then
    echo " Error: python3 is not installed. Please install Python 3.9+."
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo " Error: psql is not installed. Please install PostgreSQL client."
    exit 1
fi

# 3. Environment Variables
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot"}
export PYTHONPATH=.

# 4. Check if DB is reachable
echo "Checking database connection..."
if ! psql -d "$DATABASE_URL" -c "\q" 2>/dev/null; then
    echo " Database 'siliconpilot' not reachable or doesn't exist."
    echo "Running database restore script..."
    bash database/restore_db.sh "1Anurag2Basistha"
fi

# 5. Start Server
echo " Starting Silicon-Pilot backend server on port 8000..."
# Kill any existing server on port 8000
if [[ "$OS_NAME" == *"linux"* || "$OS_NAME" == *"darwin"* ]]; then
    fuser -k 8000/tcp 2>/dev/null || true
fi

# Run uvicorn in background
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 > server_output.log 2>&1 &
SERVER_PID=$!

echo " Waiting for server to initialize..."
sleep 5

# 6. Open Browser
URL="http://localhost:8000"
echo " Opening frontend at $URL"

if [[ "$OS_NAME" == *"darwin"* ]]; then
    open "$URL"
elif [[ "$OS_NAME" == *"linux"* ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "$URL"
    else
        echo "Please open $URL in your browser."
    fi
elif [[ "$OS_NAME" == *"mingw"* || "$OS_NAME" == *"cygwin"* || "$OS_NAME" == *"msys"* ]]; then
    start "$URL"
else
    echo "Please open $URL in your browser."
fi

echo " Silicon-Pilot is running (PID: $SERVER_PID). Press Ctrl+C to stop."
wait $SERVER_PID
