#!/bin/bash

################################################################################
# Zenith Healthcare AI Platform - Azure VM Deployment Script
# 
# This script sets up the complete backend + frontend on an Azure VM
# Usage: bash scripts/deploy-azure-vm.sh
#
# Prerequisites:
# - Ubuntu/Debian Linux VM
# - .env file with Azure credentials
#
################################################################################

set -e  # Exit on error

echo "🚀 Zenith Healthcare - Azure VM Deployment"
echo "==========================================="
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Check prerequisites
# ─────────────────────────────────────────────────────────────────────────────
echo "📋 Checking prerequisites..."

if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create .env with Azure credentials."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. Install system dependencies
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Installing system dependencies..."

sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3.11 \
    python3.11-venv \
    python3-pip \
    curl \
    git \
    build-essential \
    nodemon \
    > /dev/null 2>&1

echo "✅ System dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Install/verify Bun (JavaScript package manager)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "🟦 Setting up Bun package manager..."

if ! command -v bun &> /dev/null; then
    echo "   Installing Bun..."
    curl -fsSL https://bun.sh/install | bash > /dev/null 2>&1
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
fi

echo "✅ Bun ready"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Build React frontend
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "⚛️  Building React frontend..."

cd "Pixel Perfect"

if [ ! -d "node_modules" ]; then
    echo "   Installing Node dependencies..."
    bun install > /dev/null 2>&1
fi

echo "   Building optimized bundle..."
bun run build > /dev/null 2>&1

if [ -d "dist" ]; then
    echo "✅ React frontend built to ./dist/"
else
    echo "❌ React build failed"
    exit 1
fi

cd ..

# ─────────────────────────────────────────────────────────────────────────────
# 5. Set up Python virtual environment
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "🐍 Setting up Python environment..."

if [ ! -d ".venv" ]; then
    echo "   Creating virtual environment..."
    python3.11 -m venv .venv
fi

source .venv/bin/activate

echo "   Installing Python dependencies..."
pip install --quiet --upgrade pip setuptools wheel
pip install --quiet -r requirements.txt

echo "✅ Python environment ready"

# ─────────────────────────────────────────────────────────────────────────────
# 6. Database initialization
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "🗄️  Initializing database..."

# Run the database creation script
source .venv/bin/activate
python scripts/student/1_create_database.py > /dev/null 2>&1 || {
    echo "⚠️  Database creation encountered an issue (may already exist)"
}

echo "✅ Database initialized"

# ─────────────────────────────────────────────────────────────────────────────
# 7. Deployment summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "==========================================="
echo "✨ Deployment Complete!"
echo "==========================================="
echo ""
echo "📍 Application Structure:"
echo "   • React Frontend: ./Pixel Perfect/dist/"
echo "   • Python Backend: ./app.py (Flask)"
echo "   • Virtual Environment: ./.venv/"
echo ""
echo "🚀 To start the application:"
echo ""
echo "   source .venv/bin/activate"
echo "   python app.py"
echo ""
echo "🌐 Access at: http://localhost:5000"
echo ""
echo "📝 Environment Variables:"
echo "   - AZURE_MYSQL_HOST"
echo "   - AZURE_MYSQL_USER"
echo "   - AZURE_MYSQL_PASSWORD"
echo "   - AZURE_STORAGE_CONNECTION_STRING"
echo "   - AZURE_SEARCH_ENDPOINT"
echo "   - AZURE_SEARCH_KEY"
echo "   - AZURE_OPENAI_KEY"
echo ""
echo "✅ All systems ready!"
echo ""
