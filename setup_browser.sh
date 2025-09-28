#!/bin/bash

echo "🔧 Setting up browser dependencies for Tarzan Web Crawler"

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script needs to be run with sudo privileges"
    echo "💡 Run: sudo ./setup_browser.sh"
    exit 1
fi

echo "📦 Installing system dependencies..."

# Update package list
apt-get update

# Install required packages for Playwright
apt-get install -y \
    libnspr4 \
    libnss3 \
    libasound2 \
    libxss1 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libatspi2.0-0

echo "✅ System dependencies installed"
echo "🚀 You can now run the crawler with screenshot support!"
echo ""
echo "To test screenshots:"
echo "  source venv/bin/activate"
echo "  python main.py"