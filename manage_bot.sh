IMAGE_NAME="discordbot"
CONTAINER_NAME="discordbot"

echo "Stopping and removing existing container..."
docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null

echo "Removing existing Docker image..."
docker rmi $IMAGE_NAME 2>/dev/null

echo "Building new Docker image..."
docker build -t $IMAGE_NAME .

echo "Starting the bot..."
docker run -d --name $CONTAINER_NAME -v $(pwd):/app $IMAGE_NAME

echo "Bot has been started."
