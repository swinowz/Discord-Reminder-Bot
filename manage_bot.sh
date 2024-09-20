#!/bin/bash
IMAGE_NAME="discordbot-test"
CONTAINER_NAME="discordbot-test"

echo "Stopping and removing existing container..."
docker compose down

echo "Starting docker container..."
docker compose up -d --build

echo "Bot has been started."
