# Gemini Transcribe

A powerful audio-to-text transcription tool using Google's Gemini 3 Pro Preview API. Transcribe YouTube videos and audio files (MP3, WAV, AAC, FLAC, M4A, OGG) with AI-powered accuracy.

## Features

- 🎬 **YouTube Support** - Transcribe YouTube videos directly by URL
- 🎵 **Multi-format Audio** - Support for MP3, WAV, AAC, FLAC, M4A, OGG
- ✂️ **Audio Trimming** - Process specific portions using start/end times
- 📝 **AI Summaries** - Generate automatic summaries of transcriptions
- 📊 **Token Monitoring** - Display token counts for API usage tracking
- ☁️ **Large File Support** - Handle files >20MB via Gemini Files API
- 🧠 **Custom Instructions** - Add specific instructions for transcription
- 🌐 **Web Interface** - Deploy as a Cloud Run service with web UI
- 💾 **Save Files** - Download transcripts and audio files
- 🧹 **Auto Cleanup** - Automatic cleanup of uploaded files

## Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg (for audio processing)
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd gemini-transcribe

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows:**
Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Usage

### Command Line (CLI)

**Basic transcription:**
```bash
python gemini_transcribe_cli.py input.mp3 output.txt
```

**Transcribe YouTube video:**
```bash
python gemini_transcribe_cli.py --youtube-url "https://www.youtube.com/watch?v=VIDEO_ID" transcript.txt
```

**With summary:**
```bash
python gemini_transcribe_cli.py input.mp3 output.txt --summary summary.txt
```

**Trim audio (process only portion):**
```bash
python gemini_transcribe_cli.py input.mp3 output.txt --start 02:30 --end 10:00
```

### Web Interface

Run the Flask web application locally:
```bash
python app.py
```

Visit `http://localhost:8080` to use the web interface.

**Web UI Features:**
- Enter YouTube URL to transcribe
- Option to generate AI summary
- Option to download MP3 audio file
- Download transcript as text file

## Command-Line Options

| Option | Description |
|--------|-------------|
| `input` | Input audio file path |
| `output` | Output text file path (required) |
| `--api-key` | Gemini API key (alternative to environment variable) |
| `--youtube-url` | Download audio from YouTube URL |
| `--youtube-output` | Custom path for downloaded YouTube audio |
| `--summary FILE` | Generate summary and save to specified file |
| `--start MM:SS` | Start time for audio trimming |
| `--end MM:SS` | End time for audio trimming |
| `--system-instruction` | Custom system instruction for the model |
| `--inline` | Process audio inline (for files <20MB) |
| `--keep-uploaded` | Don't delete uploaded file after processing |
| `--help` | Show help message |

## Cloud Deployment

Deploy to Google Cloud Run with a web frontend:

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# Deploy with Cloud Build
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY="YOUR_API_KEY"
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Supported Audio Formats

- MP3
- WAV
- AAC
- FLAC
- M4A
- OGG
- AIFF

## Model Information

This tool uses **Gemini 3 Pro Preview** (`gemini-3-pro-preview`) for transcription, providing:
- High accuracy transcription
- Support for long audio files (up to 9.5 hours)
- 65,536 max output tokens for long transcriptions

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key (required) |
| `PORT` | Port for web server (default: 8080) |

### .env File

Create a `.env` file from the template:
```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_api_key_here
```

## Project Structure

```
gemini-transcribe/
├── gemini_transcribe_cli.py  # Command-line interface
├── app.py                     # Flask web application
├── templates/
│   └── index.html            # Web UI template
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container configuration
├── cloudbuild.yaml           # Cloud Build pipeline
├── DEPLOYMENT.md             # Deployment guide
├── .env.example              # Environment template
└── README.md                 # This file
```

## Troubleshooting

### FFmpeg Not Found
Ensure FFmpeg is installed and in your PATH.

### API Key Error
Verify your API key is valid at [Google AI Studio](https://aistudio.google.com/app/apikey).

### Transcription Stops Early
The tool is configured with 65,536 max output tokens. For extremely long audio, consider splitting the file.

### YouTube Download Fails
Ensure the video is publicly accessible and yt-dlp is up to date:
```bash
pip install -U yt-dlp
```

### "Failed to fetch" Error in Web UI
Check the terminal where `python app.py` is running for detailed error messages.

## License

Apache License - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
