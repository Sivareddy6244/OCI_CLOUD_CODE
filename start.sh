#!/bin/bash
# Quick start script for Multi-Cloud Portal

set -e

echo "==================================="
echo "Multi-Cloud Portal - Quick Start"
echo "==================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy .env.template to .env and configure your credentials:"
    echo "   cp .env.template .env"
    echo "   nano .env  # or use your favorite editor"
    exit 1
fi

echo "✅ Found .env file"

# Load environment variables safely
set -a
source .env
set +a

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

echo "✅ Python $(python3 --version) found"

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "⚠️  Terraform is not installed."
    echo "   Install Terraform from: https://www.terraform.io/downloads"
    echo "   Or run: sudo apt install terraform (Ubuntu/Debian)"
    echo ""
    read -p "Continue without Terraform? (VM deployment will not work) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Terraform $(terraform --version | head -n1) found"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting Multi-Cloud Portal..."
echo "   Access the application at: http://localhost:8000"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

# Start the application
cd backend
uvicorn unified_main:app --host 0.0.0.0 --port 8000 --reload
