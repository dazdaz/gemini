#!/bin/bash

# Gemini Image Generator - Setup Script
# This script sets up the virtual environment and installs dependencies

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

echo "=================================================="
echo "  Gemini Image Generator - Setup Script"
echo "=================================================="
echo ""

# Check for uv command
if command -v uv &> /dev/null; then
    log_success "uv found - using fast package management"
    USE_UV=true
else
    log_info "uv not found - using traditional Python setup"
    log_info "Install uv for faster package management: https://docs.astral.sh/uv/getting-started/installation/"
    USE_UV=false
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

log_success "Python 3 found"

# Create virtual environment if it doesn't exist
VENV_DIR="venv"
if [ "$USE_UV" = true ]; then
    VENV_DIR=".venv"
fi

if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating virtual environment..."
    if [ "$USE_UV" = true ]; then
        uv venv
    else
        python3 -m venv venv
    fi
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
log_info "Installing dependencies..."
if [ "$USE_UV" = true ]; then
    source .venv/bin/activate
    uv pip install --upgrade pip
    uv pip install -r requirements.txt
else
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi
log_success "Dependencies installed"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    log_warning "gcloud CLI not found. Please install Google Cloud SDK."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
else
    log_success "gcloud CLI found"
    
    # Check if user is authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        log_success "gcloud authentication found"
    else
        log_warning "Not authenticated with gcloud. Run: gcloud auth login"
    fi
    
    # Check if application default credentials are set
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
        log_success "Application default credentials found"
    else
        log_warning "Application default credentials not found. Run: gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform"
    fi
fi

echo ""
log_success "Setup complete!"
echo ""
echo "To use the tool:"
if [ "$USE_UV" = true ]; then
    echo "  1. Activate the virtual environment: source .venv/bin/activate"
else
    echo "  1. Activate the virtual environment: source venv/bin/activate"
fi
echo "  2. Set your project: export GOOGLE_CLOUD_PROJECT=your-project-id"
echo "  3. Test your configuration: ./run.sh test"
echo "  4. Run the tool: ./run.sh generate output.jpg -p 'A sunset'"
echo ""
echo "For first-time setup, also run:"
echo "  ./01-setup-iam-permission.sh"
echo ""
echo "Available commands:"
echo "  - test: Test configuration without API calls"
echo "  - generate: Text-to-image generation"
echo "  - edit: Image editing"
echo "  - restore: Photo restoration"
echo "  - style_transfer: Style transfer"
echo "  - compose: Creative composition"
echo "  - add_text: Add text to image"
echo "  - sketch_to_image: Sketch to image"
