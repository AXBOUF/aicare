#!/bin/bash
set -euo pipefail

# Quick Build & Push Script
# Usage:
#   Push to Docker Hub:
#     ./build-and-push.sh dockerhub <dockerhub-username> [tag]
#   Push to ACR:
#     ./build-and-push.sh acr <acr-name> [tag]

if [ "$#" -lt 2 ]; then
	cat <<EOF
Usage:
	./build-and-push.sh dockerhub <dockerhub-username> [tag]
	./build-and-push.sh acr <acr-name> [tag]

Examples:
	./build-and-push.sh dockerhub axbouf latest
	./build-and-push.sh acr aicareprod v1.0.0
EOF
	exit 1
fi

MODE="$1"           # 'dockerhub' or 'acr'
TARGET="$2"         # dockerhub username or acr name
TAG="${3:-latest}"
IMAGE_NAME="aicare"

echo "🔨 Building Docker image (tag: $TAG)..."
docker build -t ${IMAGE_NAME}:${TAG} .

if [ "$MODE" = "acr" ]; then
	ACR_NAME="$TARGET"
	REGISTRY_URL="$ACR_NAME.azurecr.io"
	FULL_IMAGE="$REGISTRY_URL/$IMAGE_NAME:$TAG"

	echo "📦 Tagging image for ACR: $FULL_IMAGE"
	docker tag ${IMAGE_NAME}:${TAG} $FULL_IMAGE

	echo "🔐 Logging into ACR ($ACR_NAME)..."
	az acr login --name $ACR_NAME

	echo "⬆️  Pushing image to ACR..."
	docker push $FULL_IMAGE

	echo "✅ Image pushed to ACR: $FULL_IMAGE"
	exit 0

elif [ "$MODE" = "dockerhub" ]; then
	DOCKERHUB_USER="$TARGET"
	FULL_IMAGE="$DOCKERHUB_USER/$IMAGE_NAME:$TAG"

	echo "📦 Tagging image for Docker Hub: $FULL_IMAGE"
	docker tag ${IMAGE_NAME}:${TAG} $FULL_IMAGE

	echo "🔐 Please login to Docker Hub if you haven't: docker login"
	echo "⬆️  Pushing image to Docker Hub..."
	docker push $FULL_IMAGE

	echo "✅ Image pushed to Docker Hub: $FULL_IMAGE"
	exit 0

else
	echo "Unknown mode: $MODE"
	echo "Use 'dockerhub' or 'acr'"
	exit 2
fi
