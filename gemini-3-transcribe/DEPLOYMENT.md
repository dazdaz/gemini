# Deployment Guide for Gemini Transcribe

This guide explains how to deploy Gemini Transcribe to Google Cloud Run.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **APIs enabled**:
   - Cloud Build API
   - Cloud Run API
   - Artifact Registry API
   - Generative Language API (for Gemini)
3. **gcloud CLI** installed and authenticated
4. **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Quick Start

### 1. Set up your environment

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  generativelanguage.googleapis.com
```

### 2. Create a Secret for API Key (Recommended)

```bash
# Store your Gemini API key as a secret
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Deploy using Cloud Build

```bash
# Option A: Pass API key directly (for testing)
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Option B: Use default substitutions (requires secret setup)
gcloud builds submit --config=cloudbuild.yaml
```

### 4. Access Your Service

After deployment, Cloud Build will output the service URL:

```
Service URL: https://gemini-transcribe-xxxxx-uc.a.run.app
```

Visit this URL to access the web interface.

## Configuration Options

### Cloud Build Substitutions

| Variable | Default | Description |
|----------|---------|-------------|
| `_REGION` | `us-central1` | GCP region for deployment |
| `_SERVICE_NAME` | `gemini-transcribe` | Cloud Run service name |
| `_REPOSITORY` | `gemini-transcribe-repo` | Artifact Registry repository name |
| `_GEMINI_API_KEY` | (required) | Your Gemini API key |

### Cloud Run Settings

The deployment configures:
- **Memory**: 2GB (for audio processing)
- **CPU**: 2 vCPUs
- **Timeout**: 15 minutes (for long videos)
- **Concurrency**: 10 requests per instance

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable (or create .env file)
export GEMINI_API_KEY="your-api-key"

# Run locally
python app.py
```

Visit `http://localhost:8080` to test locally.

## Manual Deployment (Alternative)

If you prefer to deploy manually without Cloud Build:

```bash
# Build the container
docker build -t gemini-transcribe .

# Tag for Artifact Registry
docker tag gemini-transcribe \
  us-central1-docker.pkg.dev/YOUR_PROJECT/gemini-transcribe-repo/gemini-transcribe:latest

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/YOUR_PROJECT/gemini-transcribe-repo/gemini-transcribe:latest

# Deploy to Cloud Run
gcloud run deploy gemini-transcribe \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT/gemini-transcribe-repo/gemini-transcribe:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --set-env-vars=GEMINI_API_KEY="your-api-key"
```

## Troubleshooting

### "API has not been enabled" Error
Enable the Generative Language API:
```bash
gcloud services enable generativelanguage.googleapis.com
```

### Container Build Fails
Ensure ffmpeg is installed (included in Dockerfile) and all dependencies are in requirements.txt.

### Timeout Errors for Long Videos
Increase the Cloud Run timeout (max 3600 seconds):
```bash
gcloud run services update gemini-transcribe --timeout=1800
```

## Cost Considerations

- **Cloud Run**: Pay per request and compute time
- **Artifact Registry**: Storage costs for container images
- **Gemini API**: Usage-based pricing for transcription

To minimize costs:
- Set minimum instances to 0
- Use appropriate memory/CPU settings
- Delete unused container images

## Security Best Practices

1. Use Secret Manager for API keys
2. Consider adding authentication to Cloud Run
3. Set up VPC connectors for internal services
4. Enable Cloud Audit Logs for monitoring