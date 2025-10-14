#!/bin/bash

# --- Configuration ---
# ‚ö†Ô∏è You MUST replace "your-project-id" with your actual Google Cloud Project ID.
PROJECT_ID="daev-playground"
SERVICE_ACCOUNT_NAME="chirp-transcription"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="$HOME/chirp-service-account.json"

# Auto-detect shell configuration file
if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    else
        SHELL_CONFIG="$HOME/.bash_profile"
    fi
else
    SHELL_CONFIG="$HOME/.profile"
fi

# Roles needed for the application
ROLES=(
    "roles/speech.admin"            # For Speech-to-Text API (includes recognizer creation)
    "roles/ml.developer"            # For Cloud AI Platform (TTS)
    "roles/cloudtranslate.user"     # For Translation API
)

# APIs to enable
APIS=(
    "speech.googleapis.com"
    "texttospeech.googleapis.com"
    "translate.googleapis.com"
    "aiplatform.googleapis.com"
)

# --- Error Handling ---
set -e

error_exit() {
    echo -e "\n\033[31mFATAL ERROR: $1\033[0m" >&2
    exit 1
}

# Function to check for required commands and project ID
check_prerequisites() {
    echo "Checking prerequisites..."
    if ! command -v gcloud &> /dev/null; then
        error_exit "'gcloud' command not found. Please install and initialize the gcloud CLI."
    fi
    if [ "$PROJECT_ID" == "your-project-id" ]; then
        error_exit "Please update the 'PROJECT_ID' variable in the script with your actual project ID."
    fi
    echo "Using Project ID: $PROJECT_ID"
    gcloud config set project "$PROJECT_ID" || error_exit "Failed to set project configuration. Check project existence and permissions."
    echo "---"
}

# Detect OS for sed compatibility
detect_sed() {
    if sed --version >/dev/null 2>&1; then
        # GNU sed (Linux)
        SED_INPLACE="sed -i"
    else
        # BSD sed (macOS)
        SED_INPLACE="sed -i ''"
    fi
}

# --- SETUP FUNCTION ---
setup() {
    check_prerequisites
    detect_sed

    echo -e "\n\033[32m--- STARTING SERVICE ACCOUNT SETUP ---\033[0m"

    # 0. Enable required APIs
    echo "0. Enabling required Google Cloud APIs..."
    for API in "${APIS[@]}"; do
        echo "   -> Enabling: $API"
        gcloud services enable "$API" --project="$PROJECT_ID" || echo "Warning: Failed to enable $API (may already be enabled)"
    done
    echo "APIs enabled successfully."
    echo "---"

    # 1. Create the Service Account
    echo "1. Creating Service Account: $SERVICE_ACCOUNT_NAME..."
    if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
        echo "Service Account already exists."
    else
        gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
            --display-name="Chirp Transcription Service Account" \
            --project="$PROJECT_ID" || error_exit "Failed to create service account."
        echo "Service Account created successfully."
        
        # Wait for IAM resource propagation
        echo "Waiting 10 seconds for IAM resource propagation..."
        sleep 10
    fi
    echo "---"

    # 2. Grant Required Permissions with retry logic
    echo "2. Granting IAM Roles to Service Account..."
    for ROLE in "${ROLES[@]}"; do
        echo "   -> Granting role: $ROLE"
        MAX_RETRIES=3
        RETRY_COUNT=0
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
                --role="$ROLE" \
                --condition=None \
                --no-user-output-enabled 2>/dev/null; then
                break
            else
                RETRY_COUNT=$((RETRY_COUNT + 1))
                if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                    echo "      Retry $RETRY_COUNT/$MAX_RETRIES after 5 seconds..."
                    sleep 5
                else
                    echo "      Warning: Failed to grant $ROLE after $MAX_RETRIES attempts"
                fi
            fi
        done
    done
    echo "All roles granted successfully."
    
    # Wait for IAM policy changes to propagate
    echo "Waiting 15 seconds for IAM policy propagation..."
    sleep 15
    echo "---"

    # 3. Create and Download Service Account Key
    echo "3. Creating and downloading key file to: $KEY_FILE..."
    
    # Delete old key file if it exists
    if [ -f "$KEY_FILE" ]; then
        echo "   Removing old key file..."
        rm -f "$KEY_FILE"
    fi
    
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SERVICE_ACCOUNT_EMAIL" \
        --project="$PROJECT_ID" || error_exit "Failed to create and download key."
    
    # Set secure permissions on key file
    chmod 600 "$KEY_FILE"
    echo "Key downloaded successfully with secure permissions (600)."
    echo "---"

    # 4. Set Environment Variables in Shell Configuration
    echo "4. Setting permanent environment variables in $SHELL_CONFIG..."

    # Create backup of shell config
    cp "$SHELL_CONFIG" "${SHELL_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

    # Define the lines to add/check
    CRED_LINE="export GOOGLE_APPLICATION_CREDENTIALS=\"$KEY_FILE\""
    PROJECT_LINE="export GOOGLE_CLOUD_PROJECT=\"$PROJECT_ID\""

    # Remove old entries first to avoid duplicates
    if [ -f "$SHELL_CONFIG" ]; then
        grep -v "^export GOOGLE_APPLICATION_CREDENTIALS=" "$SHELL_CONFIG" > "${SHELL_CONFIG}.tmp" || true
        grep -v "^export GOOGLE_CLOUD_PROJECT=" "${SHELL_CONFIG}.tmp" > "${SHELL_CONFIG}.tmp2" || true
        mv "${SHELL_CONFIG}.tmp2" "$SHELL_CONFIG"
        rm -f "${SHELL_CONFIG}.tmp"
    fi

    # Add new entries
    echo "" >> "$SHELL_CONFIG"
    echo "# Google Cloud credentials for Chirp Transcription" >> "$SHELL_CONFIG"
    echo "$CRED_LINE" >> "$SHELL_CONFIG"
    echo "$PROJECT_LINE" >> "$SHELL_CONFIG"

    # Set variables for the current session
    export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"
    export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
    echo "Environment variables set for current and future sessions."
    echo "---"
    
    # 5. Set Quota Project for ADC
    echo "5. Configuring Application Default Credentials quota project..."
    gcloud auth application-default set-quota-project "$PROJECT_ID" 2>/dev/null || {
        echo "Note: ADC not configured yet. Run 'gcloud auth application-default login' if needed."
    }
    echo "---"

    # 6. Verify setup
    echo "6. Verifying setup..."
    echo "   Service Account: $SERVICE_ACCOUNT_EMAIL"
    echo "   Key File: $KEY_FILE"
    echo "   Project ID: $PROJECT_ID"
    echo "   Shell Config: $SHELL_CONFIG"
    
    if [ -f "$KEY_FILE" ]; then
        echo "   ‚úì Key file exists and is readable"
    else
        error_exit "Key file was not created successfully"
    fi
    echo "---"

    # 7. Final Instructions
    echo -e "\n\033[32m‚úì SETUP COMPLETE! ‚úì\033[0m"
    echo ""
    echo "Next steps:"
    echo "1. Activate environment variables in current terminal:"
    echo -e "   \033[33msource $SHELL_CONFIG\033[0m"
    echo ""
    echo "2. Set your Gemini API key:"
    echo -e "   \033[33mexport GEMINI_API_KEY='your-api-key-here'\033[0m"
    echo ""
    echo "3. Run your application:"
    echo -e "   \033[33mpython3 app.py\033[0m"
    echo ""
    echo "Note: It may take a few minutes for permissions to fully propagate."
    echo ""
}

# --- CLEANUP FUNCTION ---
cleanup() {
    check_prerequisites
    detect_sed
    
    echo -e "\n\033[31m--- STARTING SERVICE ACCOUNT CLEANUP ---\033[0m"
    echo "This will remove the service account and all associated resources."
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi

    # 1. List and delete all keys for the service account
    echo "1. Deleting service account keys..."
    KEYS=$(gcloud iam service-accounts keys list \
        --iam-account="$SERVICE_ACCOUNT_EMAIL" \
        --project="$PROJECT_ID" \
        --filter="keyType:USER_MANAGED" \
        --format="value(name)" 2>/dev/null || true)
    
    if [ -n "$KEYS" ]; then
        while IFS= read -r KEY; do
            echo "   -> Deleting key: $KEY"
            gcloud iam service-accounts keys delete "$KEY" \
                --iam-account="$SERVICE_ACCOUNT_EMAIL" \
                --project="$PROJECT_ID" \
                --quiet || echo "      Warning: Failed to delete key"
        done <<< "$KEYS"
    else
        echo "   No keys found to delete."
    fi
    echo "---"

    # 2. Remove IAM Roles
    echo "2. Removing IAM Roles from Service Account..."
    for ROLE in "${ROLES[@]}"; do
        echo "   -> Removing role: $ROLE"
        gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="$ROLE" \
            --all 2>/dev/null || echo "      Note: Role may not exist"
    done
    echo "IAM roles removal attempted."
    echo "---"

    # 3. Delete local key file
    echo "3. Deleting local key file: $KEY_FILE..."
    if [ -f "$KEY_FILE" ]; then
        rm -f "$KEY_FILE"
        echo "Key file deleted."
    else
        echo "Key file not found, skipping."
    fi
    
    # Delete backups older than 7 days
    find "$HOME" -name "chirp-service-account.json.backup.*" -mtime +7 -delete 2>/dev/null || true
    echo "---"

    # 4. Delete the Service Account
    echo "4. Deleting Service Account: $SERVICE_ACCOUNT_NAME..."
    gcloud iam service-accounts delete "$SERVICE_ACCOUNT_EMAIL" \
        --project="$PROJECT_ID" \
        --quiet 2>/dev/null || echo "Note: Service account may not exist"
    echo "Service Account deletion attempted."
    echo "---"

    # 5. Clean up Shell Configuration
    echo "5. Removing environment variables from $SHELL_CONFIG..."
    
    if [ -f "$SHELL_CONFIG" ]; then
        # Create backup
        cp "$SHELL_CONFIG" "${SHELL_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Remove the Google Cloud credentials section
        grep -v "^export GOOGLE_APPLICATION_CREDENTIALS=" "$SHELL_CONFIG" > "${SHELL_CONFIG}.tmp" || true
        grep -v "^export GOOGLE_CLOUD_PROJECT=" "${SHELL_CONFIG}.tmp" > "${SHELL_CONFIG}.tmp2" || true
        grep -v "^# Google Cloud credentials for Chirp Transcription" "${SHELL_CONFIG}.tmp2" > "$SHELL_CONFIG" || true
        rm -f "${SHELL_CONFIG}.tmp" "${SHELL_CONFIG}.tmp2"
    fi
    
    # Unset variables for the current session
    unset GOOGLE_APPLICATION_CREDENTIALS
    unset GOOGLE_CLOUD_PROJECT
    
    echo "Environment variables removed from $SHELL_CONFIG and unset in current session."
    echo "---"
    
    echo -e "\n\033[32m‚úì CLEANUP COMPLETE! ‚úì\033[0m"
    echo ""
    echo "To finalize cleanup in your current terminal:"
    echo -e "\033[33msource $SHELL_CONFIG\033[0m"
    echo ""
}

# --- Script Entry Point ---

if [ -z "$1" ]; then
    echo "Usage: bash sa_manager.sh [setup|cleanup]"
    echo ""
    echo "Commands:"
    echo "  setup   - Create service account and configure credentials"
    echo "  cleanup - Remove service account and all associated resources"
    exit 1
fi

case "$1" in
    setup)
        setup
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Invalid argument: $1"
        echo "Usage: bash sa_manager.sh [setup|cleanup]"
        exit 1
        ;;
esac

