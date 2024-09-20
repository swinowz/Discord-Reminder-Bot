#!/bin/bash
chown -R botuser:botuser /app
su botuser -c "pip install --no-cache-dir --upgrade pip"
su botuser -c "pip install --no-cache-dir -r /app/requirements.txt"
su botuser -c "python /app/bot.py"