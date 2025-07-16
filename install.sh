#!/bin/bash
# Quick installation script for Python Sandbox MCP Server

set -e

echo "🚀 Installing Python Sandbox MCP Server..."
echo

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.9 or later and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Found Python $PYTHON_VERSION"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the project root directory."
    exit 1
fi

# Try to use uv first, fall back to pip
if command -v uv &> /dev/null; then
    echo "📦 Installing dependencies with uv..."
    uv sync
    echo "✅ Dependencies installed with uv"
else
    echo "📦 uv not found, installing with pip..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "🔧 Creating virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    echo "✅ Dependencies installed with pip"
fi

echo
echo "🎉 Installation complete!"
echo
echo "To start the server:"
echo "  python run.py"
echo
echo "To start in debug mode:"
echo "  python run.py --debug"
echo
echo "To run with authentication:"
echo "  python run.py --api-key your-secret-key"
echo
echo "For more options:"
echo "  python run.py --help"
echo
echo "📚 Check the README.md for detailed usage instructions."