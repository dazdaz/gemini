#!/bin/bash

# Gemini Image Generator - IAM Setup Script
# This script sets up necessary permissions for Vertex AI and GCS access

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Script Options ---
VERBOSE=false
DEBUG=false
REMOVE=false

# --- Robust Argument Parsing ---
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -d|--debug)
            DEBUG=true
            VERBOSE=true
            shift
            ;;
        -r|--remove)
            REMOVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose    Verbose mode"
            echo "  -d, --debug      Debug mode (implies verbose)"
            echo "  -r, --remove     Remove IAM permissions and clean up"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        -*)
            echo "Invalid option: $1" >&2
            echo "Usage: $0 [-v|--verbose] [-d|--debug] [-r|--remove] [-h|--help]"
            exit 1
            ;;
        *)
            # Stop parsing at the first non-option argument
            break
            ;;
    esac
done


# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[‚Äö√∫√Æ]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${GREEN}[STEP]${NC} $1"
    echo "=================================================="
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

log_debug() {
    if [ "$DEBUG" = true ]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Print header
echo "=================================================="
if [ "$REMOVE" = true ]; then
    echo "  Gemini Image Generator - IAM Cleanup Script"
else
    echo "  Gemini Image Generator - IAM Setup Script"
fi
echo "=================================================="
echo ""

if [ "$DEBUG" = true ]; then
    log_warning "Debug mode enabled - detailed output will be shown"
    set -x  # Enable command tracing
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi
log_success "gcloud CLI found"

# Get current project and user
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
CURRENT_USER=$(gcloud config get-value account 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    log_error "No project configured. Run 'gcloud config set project PROJECT_ID'"
    exit 1
fi

if [ -z "$CURRENT_USER" ]; then
    log_error "Not authenticated. Run 'gcloud auth login'"
    exit 1
fi

log_info "Project: ${PROJECT_ID}"
log_info "User: ${CURRENT_USER}"
echo ""

# Function to remove IAM permissions
remove_permissions() {
    log_step "Removing IAM Permissions..."

    ROLES=(
        "roles/aiplatform.user"
        "roles/aiplatform.admin"
        "roles/storage.objectViewer"
        "roles/storage.objectCreator"
        "roles/serviceusage.serviceUsageConsumer"
    )

    # Remove user permissions
    log_info "Removing permissions from user: $CURRENT_USER"
    for role in "${ROLES[@]}"; do
        log_verbose "Removing $role from $CURRENT_USER..."

        if gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
            --member="user:$CURRENT_USER" \
            --role="$role" \
            --quiet --condition=None > /tmp/iam_remove.log 2>&1; then
            log_success "$role removed successfully"
        else
            log_warning "Could not remove $role (may not have been assigned)"
            if [ "$DEBUG" = true ]; then
                cat /tmp/iam_remove.log
            fi
        fi
    done

    # Remove ADC
    ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"
    if [ -f "$ADC_FILE" ]; then
        read -p "Remove Application Default Credentials? (y/N): " remove_adc
        if [[ $remove_adc =~ ^[Yy]$ ]]; then
            rm -f "$ADC_FILE"
            log_success "Application Default Credentials removed"
        fi
    fi

    log_step "Cleanup Complete!"
    log_success "IAM permissions have been removed"
    echo ""
}

# If --remove flag is set, run cleanup and exit
if [ "$REMOVE" = true ]; then
    read -p "This will remove IAM permissions. Continue? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_warning "Cleanup cancelled by user"
        exit 0
    fi
    remove_permissions
    exit 0
fi

# Confirm before proceeding
read -p "Continue with IAM setup? (Y/n): " confirm
if [[ $confirm =~ ^[Nn]$ ]]; then
    log_warning "Setup cancelled by user"
    exit 0
fi
echo ""

# Step 1: Enable required APIs
log_step "Step 1: Enabling required APIs..."

APIS=(
    "aiplatform.googleapis.com"
    "storage-api.googleapis.com"
    "storage-component.googleapis.com"
    "iam.googleapis.com"
    "serviceusage.googleapis.com"
)

for api in "${APIS[@]}"; do
    log_verbose "Checking if $api is enabled..."

    if gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"; then
        log_success "$api already enabled"
    else
        log_info "Enabling $api..."
        if gcloud services enable "$api" --project="$PROJECT_ID" 2>&1 | tee /tmp/gcloud_enable.log; then
            log_success "$api enabled successfully"
        else
            log_error "Failed to enable $api"
            if [ "$VERBOSE" = true ]; then
                cat /tmp/gcloud_enable.log
            fi
            exit 1
        fi
    fi
done

# Step 2: Grant permissions to user
log_step "Step 2: Granting permissions to user..."

# These roles are sufficient for using Vertex AI and GCS for this tool.
# aiplatform.admin is redundant if aiplatform.user is present for prediction.
# We grant both for generality, but aiplatform.user is the key one for the error.
ROLES=(
    "roles/aiplatform.user"                 # Required for predict permissions
    "roles/storage.objectViewer"            # Read from GCS
    "roles/storage.objectCreator"           # Write to GCS
    "roles/serviceusage.serviceUsageConsumer" # Use services
)

for role in "${ROLES[@]}"; do
    log_info "Granting $role to $CURRENT_USER..."

    # The command is idempotent; it won't fail if the binding already exists.
    if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="user:$CURRENT_USER" \
        --role="$role" \
        --quiet > /tmp/iam_binding.log 2>&1; then
        log_success "$role granted successfully"
    else
        log_error "Failed to grant $role"
        if [ "$VERBOSE" = true ]; then
            cat /tmp/iam_binding.log
        fi
    fi
done


# Step 3: Set up Application Default Credentials
log_step "Step 3: Setting up Application Default Credentials..."

ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"

# Check for conflicting GOOGLE_APPLICATION_CREDENTIALS
if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    log_warning "GOOGLE_APPLICATION_CREDENTIALS is set to: $GOOGLE_APPLICATION_CREDENTIALS"
    log_warning "This may override Application Default Credentials"
    read -p "Do you want to unset GOOGLE_APPLICATION_CREDENTIALS for this session? (Y/n): " unset_var
    if [[ ! $unset_var =~ ^[Nn]$ ]]; then
        unset GOOGLE_APPLICATION_CREDENTIALS
        log_success "GOOGLE_APPLICATION_CREDENTIALS unset for this session"
        log_info "To make this permanent, add 'unset GOOGLE_APPLICATION_CREDENTIALS' to your shell profile."
    fi
fi

log_info "Refreshing Application Default Credentials..."
log_warning "This may open a browser window for authentication"
echo ""

# Use only the cloud-platform scope which covers everything needed
if gcloud auth application-default login \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --quiet 2>&1 | tee /tmp/adc_setup.log; then
    log_success "Application Default Credentials configured successfully"
else
    log_error "Failed to configure Application Default Credentials"
    if [ "$VERBOSE" = true ]; then
        cat /tmp/adc_setup.log
    fi
    exit 1
fi

# Step 4: Setting environment variables
log_step "Step 4: Setting environment variables..."
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
log_success "GOOGLE_CLOUD_PROJECT set to: $PROJECT_ID"

echo ""
log_info "To make this permanent, add to your shell profile (~/.bashrc or ~/.zshrc):"
echo "  export GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

# Wait for IAM propagation
log_step "Step 5: Waiting for IAM changes to propagate..."
log_info "Waiting 10 seconds for IAM policies to propagate..."
sleep 10
log_success "IAM propagation wait completed"

# Clean up temp files
if [ "$DEBUG" = false ]; then
    rm -f /tmp/gcloud_enable.log /tmp/iam_binding.log /tmp/adc_setup.log /tmp/iam_remove.log 2>/dev/null
fi

echo ""
log_step "Setup Complete!"
log_success "IAM permissions have been configured"
log_info "You can now use the aiphoto-tool.py script"
echo ""
log_info "Next steps:"
echo "  1. If not already done, add to your shell profile:"
echo "     export GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "  2. Run the tool: ./aiphoto-tool.py generate output.jpg -p 'A sunset'"
echo ""
log_info "To remove permissions later, run: $0 --remove"
echo ""

if [ "$VERBOSE" = true ]; then
    log_verbose "Current IAM policy for user $CURRENT_USER:"
    gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:user:$CURRENT_USER" \
        --format="table(bindings.role)"
fi
