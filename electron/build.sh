#!/bin/bash

# TradingCrew Desktop Build Script
# Builds standalone Electron app for macOS/Linux

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "TradingCrew Desktop Builder"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Node.js $(node --version)"
echo -e "${GREEN}✓${NC} npm $(npm --version)"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.11+ from https://www.python.org/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $(python3 --version)"
echo ""

# Navigate to electron directory
cd "$SCRIPT_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
    echo ""
fi

# Check for icons
if [ ! -f "assets/icon.png" ]; then
    echo -e "${YELLOW}Warning: Icon files not found in assets/${NC}"
    echo "The app will build but won't have custom icons."
    echo "See assets/ICONS_README.md for instructions."
    echo ""
fi

# Determine platform
PLATFORM=$(uname -s)
BUILD_TARGET=""

case "$PLATFORM" in
    Darwin)
        echo "Building for macOS..."
        BUILD_TARGET="mac"
        ;;
    Linux)
        echo "Building for Linux..."
        BUILD_TARGET="linux"
        ;;
    *)
        echo -e "${RED}Unsupported platform: $PLATFORM${NC}"
        exit 1
        ;;
esac

# Ask for build type
echo ""
echo "Build options:"
echo "1) Quick test (--dir, unpacked)"
echo "2) Full distributable (DMG/AppImage/etc)"
echo ""
read -p "Choose option (1 or 2): " BUILD_OPTION

case "$BUILD_OPTION" in
    1)
        echo ""
        echo -e "${YELLOW}Building unpacked app for testing...${NC}"
        npm run pack
        ;;
    2)
        echo ""
        echo -e "${YELLOW}Building full distributable...${NC}"
        npm run build:$BUILD_TARGET
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

# Check build output
if [ -d "../dist" ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Output directory: $PROJECT_ROOT/dist"
    echo ""
    ls -lh "$PROJECT_ROOT/dist" | tail -n +2
    echo ""

    if [ "$BUILD_OPTION" == "1" ]; then
        echo "To test the app:"
        echo "  ./dist/mac-arm64/TradingCrew.app/Contents/MacOS/TradingCrew  (macOS Apple Silicon)"
        echo "  ./dist/mac-x64/TradingCrew.app/Contents/MacOS/TradingCrew    (macOS Intel)"
        echo "  ./dist/linux-unpacked/tradingcrew-desktop                    (Linux)"
    else
        echo "To install:"
        echo "  macOS: Open the .dmg file"
        echo "  Linux: Install the .AppImage, .deb, or .rpm"
    fi
else
    echo -e "${RED}Build failed - dist directory not found${NC}"
    exit 1
fi

echo ""
