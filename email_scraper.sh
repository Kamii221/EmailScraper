#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "  __  __ _       _    _      ____  _ _ "
echo " |  \/  (_)     | |  | |    / ___|(_) |"
echo " | |\/| | |_   _| |  | |___| |     _| |"
echo " | |  | | | | | | |/\| |_  / |___ | | |"
echo " |_|  |_|_|\__, |_/  \_/ /  \____||_|_|"
echo "            |___/                       "
echo -e "${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo -e "${YELLOW}Installing Python 3...${NC}"
    sudo apt update && sudo apt install -y python3 python3-pip
fi

# Check if required Python packages are installed
check_python_packages() {
    local packages=("requests" "beautifulsoup4")
    for package in "${packages[@]}"; do
        if ! python3 -c "import $package" &> /dev/null; then
            echo -e "${YELLOW}Installing required package: $package${NC}"
            pip3 install $package
        fi
    done
}

# Make the Python script executable
chmod +x "$(dirname "$0")/email_scraper.py"

# Function to display help
show_help() {
    echo -e "${GREEN}Email Scraper - Command Line Interface${NC}"
    echo ""
    echo "Usage:"
    echo "  ./email_scraper.sh [options] URL"
    echo ""
    echo "Options:"
    echo "  -o, --output FILE    Save results to specified file"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./email_scraper.sh https://example.com"
    echo "  ./email_scraper.sh -o results.txt https://example.com"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            if [[ -z "$URL" ]]; then
                URL="$1"
            else
                echo -e "${RED}Error: Unexpected argument: $1${NC}"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate URL
if [[ -z "$URL" ]]; then
    echo -e "${RED}Error: URL is required${NC}"
    show_help
    exit 1
fi

# Check Python packages
check_python_packages

# Build the command
CMD="python3 $(dirname "$0")/email_scraper.py"

if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD --output $OUTPUT_FILE"
fi

CMD="$CMD $URL"

# Execute the command
eval "$CMD" 
