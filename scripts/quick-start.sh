#!/bin/bash

################################################################################
# Zenith Healthcare - Local Development Quick Start
# 
# This script builds the React frontend and runs Flask backend locally
# Usage: bash scripts/quick-start.sh
#
################################################################################

set -e

echo "🚀 Zenith Healthcare - Local Quick Start"
echo "========================================"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check .env
# ─────────────────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "   Please create .env with:"
    echo "   - AZURE_MYSQL_HOST"
    echo "   - AZURE_MYSQL_USER"
    echo "   - AZURE_MYSQL_PASSWORD"
    echo "   - AZURE_STORAGE_CONNECTION_STRING"
    echo "   - etc. (see .env.example)"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Build React
# ─────────────────────────────────────────────────────────────────────────────
echo "⚛️  Building React frontend..."
cd "Pixel Perfect"

if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    bun install
fi

echo "   Building..."
bun run build

if [ ! -d "dist" ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ React built to Pixel Perfect/dist/"
cd ..

# ─────────────────────────────────────────────────────────────────────────────
# Python setup
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "🐍 Setting up Python..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install/upgrade pip
pip install --quiet --upgrade pip > /dev/null

# Install requirements
echo "   Installing dependencies..."
pip install --quiet -r requirements.txt

echo "✅ Python environment ready"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "✨ Ready to run!"
echo "========================================"
echo ""
echo "To start the Flask app:"
echo ""
echo "  source .venv/bin/activate"
echo "  python app.py"
echo ""
echo "Then visit: http://localhost:5000"
echo ""
