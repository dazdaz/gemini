#!/bin/bash
set -x

# Get the directory of the script and move to the project root
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR/.."

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Define server ports, using environment variables if available
export PORT=${PORT:-8081}
export FRONTEND_PORT=${FRONTEND_PORT:-8000}

# --- Stop Servers Function ---
# Finds and stops processes running on the specified server ports.
stop_servers() {
    echo "Checking for and stopping existing server processes..."
    
    # Find and kill process on backend port
    BACKEND_PID=$(lsof -t -i:$PORT)
    if [ -n "$BACKEND_PID" ]; then
        echo "Found backend process (PID: $BACKEND_PID) on port $PORT. Stopping it..."
        kill $BACKEND_PID
    else
        echo "No process found on backend port $PORT."
    fi

    # Find and kill process on frontend port
    FRONTEND_PID=$(lsof -t -i:$FRONTEND_PORT)
    if [ -n "$FRONTEND_PID" ]; then
        echo "Found frontend process (PID: $FRONTEND_PID) on port $FRONTEND_PORT. Stopping it..."
        kill $FRONTEND_PID
    else
        echo "No process found on frontend port $FRONTEND_PORT."
    fi
    echo "Server cleanup finished."
    echo # Add a newline for readability
}

# --- Main Script Logic ---

# Handle 'stop' argument
if [ "$1" == "stop" ]; then
    stop_servers
    exit 0
fi

# --- Start Servers ---

# 1. Stop any currently running servers
stop_servers

# 2. Start the backend server
echo "Starting backend server on port $PORT..."
echo "Check backend.log for server status and errors."
(
    set -ex
    cd server
    echo "Activating virtual environment from .venv..."
    source .venv/bin/activate
    echo "Starting python server: server.py"
    python3 server.py
) > backend.log 2>&1 &

# 3. Start the frontend server
echo "Starting frontend server on port $FRONTEND_PORT..."
(cd client && python3 -m http.server $FRONTEND_PORT) &

# --- Output Information ---
echo
echo "----------------------------------------"
echo "Servers are launching in the background."
echo "Backend (WebSocket): ws://localhost:$PORT"
echo "Frontend (HTTP):     http://localhost:$FRONTEND_PORT/index.html"
echo "----------------------------------------"
echo
echo "To stop all servers, run:"
echo "  ./server/start.sh stop"
echo
echo "To view backend logs, run:"
echo "  tail -f backend.log"
