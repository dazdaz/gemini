#!/bin/bash

# Gemini Image Generator - Run Script
# This script activates the virtual environment and runs the tool

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[‚úì]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check for virtual environment (uv first, then traditional)
if [ -d ".venv" ]; then
    log_info "Activating uv virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    log_info "Activating traditional virtual environment..."
    source venv/bin/activate
else
    log_error "Virtual environment not found. Please run ./setup.sh first."
    log_info "Or create manually:"
    log_info "  With uv: uv venv && source .venv/bin/activate && uv pip install -r requirements.txt"
    log_info "  With Python: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if GOOGLE_CLOUD_PROJECT is set
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    log_warning "GOOGLE_CLOUD_PROJECT environment variable not set."
    
    # Try to get project from gcloud config
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -n "$PROJECT_ID" ]; then
        log_info "Setting GOOGLE_CLOUD_PROJECT from gcloud config: $PROJECT_ID"
        export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
    else
        log_error "Please set GOOGLE_CLOUD_PROJECT environment variable or run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi

log_success "Using project: $GOOGLE_CLOUD_PROJECT"

# Run the tool with all arguments
log_info "Running: python aiphoto-tool.py $@"
export GOOGLE_API_KEY="abcdefghijklmnop"
python aiphoto-tool.py "$@"
