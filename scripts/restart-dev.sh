#!/bin/bash
# Restart development servers (for Claude Code)
# Kills any existing servers and starts new ones in the background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Kill existing servers
echo "Stopping existing servers..."
pkill -f "uvicorn clutchchess.main:app" 2>/dev/null || true
pkill -f "vite.*clutchchess" 2>/dev/null || true
sleep 1

# Start backend
echo "Starting backend..."
cd "$PROJECT_DIR/server"
uv run uvicorn clutchchess.main:app --reload --port 8000 > /tmp/clutchchess-backend.log 2>&1 &

# Start frontend
echo "Starting frontend..."
cd "$PROJECT_DIR/client"
npm run dev > /tmp/clutchchess-frontend.log 2>&1 &

# Wait for servers to be ready
sleep 3

# Verify
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "Backend ready: http://localhost:8000"
else
    echo "Backend may still be starting (check /tmp/clutchchess-backend.log)"
fi

if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "Frontend ready: http://localhost:5173"
else
    echo "Frontend may still be starting (check /tmp/clutchchess-frontend.log)"
fi
