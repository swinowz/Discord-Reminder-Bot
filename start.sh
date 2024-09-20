#!/bin/bash
chown -R botuser:botuser /app
su botuser -c "python /app/bot.py"