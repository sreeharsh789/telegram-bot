#!/bin/bash

# Make the script executable
chmod +x start.sh

# Start the Flask gateway server in the background
echo "Starting Flask gateway server..."
python3 gateway.py &

# Wait a moment for the gateway to start
sleep 2

# Start the Telegram bot
echo "Starting Telegram bot..."
python3 bot.py

# Keep both processes running
wait