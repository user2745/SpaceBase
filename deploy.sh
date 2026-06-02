#!/bin/bash
# Simple CI/CD deployment script for SpaceBase

echo "🚀 Deploying SpaceBase to Production..."

# 1. Pull latest code from Git (if using git on server)
# git pull origin main

# 2. Build and restart containers in background
docker compose down
docker compose up --build -d

echo "✅ Deployment completed successfully!"
docker compose ps
