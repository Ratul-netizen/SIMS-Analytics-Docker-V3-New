#!/bin/bash
set -e

# Start cron service
service cron start

# Run database migrations
flask db upgrade

# Start the Flask server immediately
flask run --host=0.0.0.0 --port=5000 &

# Store the Flask server PID
FLASK_PID=$!

# Run initial data fetch in background (non-blocking)
flask fetch-exa &

# Wait for the Flask server process
wait $FLASK_PID 