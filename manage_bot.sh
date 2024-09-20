#!/bin/bash
IMAGE_NAME="discordbot"
CONTAINER_NAME="discordbot"

echo "Stopping and removing existing container..."
docker compose down

echo "Building new Docker image..."
docker compose up -d --build

echo "Bot has been started."
