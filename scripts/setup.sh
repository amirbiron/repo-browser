#!/bin/bash

echo "🚀 Multi-Repo Browser - Setup Script"
echo "===================================="
echo ""

# Check Python version
echo "📦 Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate || { echo "❌ Failed to activate venv"; exit 1; }

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt || { echo "❌ Failed to install dependencies"; exit 1; }

# Create .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set your MongoDB URI (and MONGODB_DB_NAME if needed)"
fi

# Create repos directory
echo "📁 Creating repos directory..."
mkdir -p /var/data/repos 2>/dev/null || mkdir -p ./repos

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and set MONGODB_URI (or MONGODB_DB_NAME if no DB in URI)"
echo "2. Run: source venv/bin/activate"
echo "3. Run: flask run --debug"
echo ""
