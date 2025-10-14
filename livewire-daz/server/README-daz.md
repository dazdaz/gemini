
git clone -b feat/live-computer-use https://github.com/heiko-hotz/generative-ai.git
cd generative-ai/gemini/multimodal-live-api/project-livewire/

Don't forget to edit .env with your project name and GEMINI API Key

I modified cloudbuild.yaml

I edited `/app/config/config.py` and modify the `initialize` method to skip the weather API key initialization:

I disabled the weather functionality as I couldn't create an account on openweatherhttps://openweathermap.org/api

```python
async def initialize(self):
    """Initialize API configuration with keys from Secret Manager"""
    try:
        # Comment out or remove the weather API key initialization
        # self.weather_api_key = get_secret("OPENWEATHER_API_KEY")
        self.weather_api_key = None  # Set to None to disable weather functionality
        logger.info("Weather API functionality disabled")
    except Exception as e:
        logger.warning(f"Weather API disabled: {str(e)}")
        self.weather_api_key = None
```

setup-livewire.sh
```bash
#!/bin/bash

# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com

# Create service account
gcloud iam service-accounts create livewire-backend --display-name="Livewire Backend"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:livewire-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:livewire-backend@${PROJECT_ID}.iam.gserviceaccount.com"     --role="roles/aiplatform.user"

gcloud iam service-accounts keys create ~/livewire-sa-key.json \
    --iam-account=livewire-backend@${PROJECT_ID}.iam.gserviceaccount.com

export GOOGLE_APPLICATION_CREDENTIALS=~/livewire-sa-key.json

PROJECT_NUMBER=$(gcloud projects describe daev-playground --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# Submit the build
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
gcloud run services describe livewire-backend --platform managed --region us-central1 --format 'value(status.url)'
gcloud run services describe livewire-backend --region us-central1
```


```
Looking at your logs, the issue is clear: the WebSocket connection is failing because it can't find the OpenWeather API key in Google Secret Manager. Here's what's happening:

## The Problem

1. **WebSocket connects successfully** - The connection handshake works
2. **Configuration fails** - When trying to initialize the Gemini session, it attempts to fetch the OpenWeather API key from Secret Manager
3. **Secret not found** - `404 Secret [projects/1234567890/secrets/OPENWEATHER_API_KEY] not found or has no versions`
4. **Connection closes** - The error causes the WebSocket to close immediately

## Solution

You need to create the OpenWeather API key secret in Google Secret Manager:

### Step 1: Get an OpenWeather API Key
If you don't have one:
1. Go to https://openweathermap.org/api
2. Sign up for a free account
3. Get your API key from the dashboard

### Step 2: Create the Secret in Google Secret Manager

```bash
# Create the secret with your OpenWeather API key
echo -n "YOUR_OPENWEATHER_API_KEY_HERE" | gcloud secrets create OPENWEATHER_API_KEY \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$PROJECT

# Grant the service account access to read the secret
gcloud secrets add-iam-policy-binding OPENWEATHER_API_KEY \
    --member="serviceAccount:livewire-backend@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT
```

### Step 3: Verify the Secret Was Created

```bash
PROJECT=my-project

# List your secrets
gcloud secrets list --project=$PROJECT

# Verify the secret value (optional)
gcloud secrets versions access latest --secret="OPENWEATHER_API_KEY" --project=$PROJECT
```

### Step 4: Test the WebSocket Connection Again

```bash
# Install wscat if you haven't already
npm install -g wscat

# Test the connection
wscat -c wss://livewire-backend-1234567890.us-central1.run.app/ws
```

## Alternative: Make Weather API Optional

If you don't need weather functionality, you could modify your backend code to make the OpenWeather API optional. In your `config/config.py`, you could change the initialization to handle missing weather API gracefully:
```