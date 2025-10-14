## README.md

```markdown
# MP3 to Text Converter with Gemini API, by using Gemini 2.5 Flash LLM.

A Python script that converts audio files (MP3, WAV, AAC, FLAC, M4A, OGG) to text using Google's Gemini API.
Features include audio trimming, automatic summarization, and support for large files through the
Gemini Files API.

https://ai.google.dev/gemini-api/docs/audio

## Features

- ✅ Convert various audio formats to text
- ✂️ Trim audio files by specifying start and end times
- 📝 Generate automatic summaries of transcriptions
- 📊 Display token count for API usage monitoring
- ☁️ Handle large files (>20MB) via Gemini Files API
- 🧠 Custom system instructions support
- 🧹 Automatic cleanup of uploaded files
- 🎵 Download YouTube audio directly to MP3 via built-in workflow

## Prerequisites

- Python 3.7+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

1. Clone this repository or download the script:
```bash
git clone <repository-url>
cd gemini-25-audio
```

2. Install required dependencies:
```bash
# 1. Create a virtual environment using uv, specifying Python 3.12
uv venv --python python3.12

# 2. Activate the newly created environment
source .venv/bin/activate

# 3. Install the dependencies from your requirements.txt file
uv pip install -r requirements.txt
```

Or install manually:
```bash
uv pip install google-generativeai pydub yt-dlp
```

3. Install FFmpeg (required for audio processing):

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Configuration


Set your Gemini API key as an environment variable:

export GEMINI_API_KEY="your-api-key-here"

Or pass it directly as a command-line argument with --api-key. 2. Enable the Generative Language API: You can enable the API using either the Google Cloud Console or the gcloud CLI:


Option 1: Google Cloud Console:

Go to https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com

Select the project associated with your API key (or create a new one at https://console.cloud.google.com/projectcreate)

Click "Enable" to activate the Generative Language API

Ensure your API key has the necessary permissions


Option 2: gcloud CLI:

Ensure gcloud is installed and initialized
```bash
gcloud init
```

Set your project (replace YOUR_PROJECT_ID with your Google Cloud project ID):
```bash
gcloud config set project YOUR_PROJECT_ID
```


Enable the Generative Language API:
```bash
gcloud services enable generativelanguage.googleapis.com
```

Verify the API is enabled:
```bash
gcloud services list --enabled | grep generativelanguage.googleapis.com
```

Or pass it directly as a command-line argument.

## Usage

### Basic Usage

Convert an MP3 file to text:
```bash
python mp3_to_text.py input.mp3 output.txt
```

### Download Audio from YouTube

Download audio from a YouTube URL and process it directly. Provide the MP3 destination path as the first positional argument when using `--youtube-url`, or supply `--youtube-output` to place the file elsewhere.

```bash
python mp3_to_text.py downloads/video.mp3 transcript.txt --youtube-url https://youtu.be/VIDEO_ID
```

### With API Key

```bash
python mp3_to_text.py input.mp3 output.txt --api-key YOUR_API_KEY
```

### Generate Summary

Create both transcription and summary:
```bash
python mp3_to_text.py input.mp3 output.txt --summary summary.txt
```

### Trim Audio

Process only a portion of the audio file:
```bash
python mp3_to_text.py input.mp3 output.txt --start 01:30 --end 05:45
```

### Custom System Instructions

Add specific instructions for transcription:
```bash
python mp3_to_text.py input.mp3 output.txt --system-instruction "Include timestamps for each speaker change"
```

### Help

Display all available options:
```bash
python mp3_to_text.py --help
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `input` | Input audio file path (required) |
| `output` | Output text file path (required) |
| `--api-key` | Gemini API key (alternative to environment variable) |
| `--summary FILE` | Generate summary and save to specified file |
| `--start MM:SS` | Start time for audio trimming |
| `--end MM:SS` | End time for audio trimming |
| `--system-instruction` | Custom system instruction for the model |
| `--keep-uploaded` | Don't delete uploaded file from Gemini after processing |
| `--youtube-url` | Download audio from the specified YouTube video before transcription |
| `--youtube-output` | Override the destination MP3 file or directory for YouTube downloads |
| `--help` | Show help message and exit |

## Examples

### Example 1: Basic Transcription
```bash
python mp3_to_text.py podcast.mp3 transcript.txt
```

### Example 2: Transcribe with Summary
```bash
python mp3_to_text.py interview.mp3 interview_text.txt --summary interview_summary.txt
```

### Example 3: Process Audio Segment
```bash
python mp3_to_text.py lecture.mp3 lecture_notes.txt --start 05:00 --end 15:30
```

### Example 4: Custom Instructions
```bash
python mp3_to_text.py meeting.mp3 minutes.txt \
    --system-instruction "Format as meeting minutes with action items" \
    --summary meeting_summary.txt
```

### Example 5: Download from YouTube
```bash
python mp3_to_text.py downloads/lecture.mp3 lecture_notes.txt \
    --youtube-url https://youtu.be/VIDEO_ID \
    --summary lecture_summary.txt
```
If you see HTTP errors, ensure the provided URL is publicly accessible and FFmpeg is installed (yt-dlp relies on it to convert audio).
## Supported Audio Formats

- MP3
- WAV
- AAC
- FLAC
- M4A
- OGG

## Token Usage

The script displays token counts for:
- Audio file transcription
- Summary generation (if requested)

This helps monitor API usage and costs.

## File Size Handling

The script automatically uses the Gemini Files API to handle audio files of any size, including those larger than 20MB. Files are:
1. Uploaded to Gemini's servers
2. Processed for transcription
3. Automatically deleted after processing (unless `--keep-uploaded` is used)

## Error Handling

The script includes comprehensive error handling for:
- Missing or invalid files
- Unsupported audio formats
- Invalid time formats
- API errors
- Network issues

## Requirements File

Create a `requirements.txt` file:
```txt
google-generativeai>=0.3.0
pydub>=0.25.1
```

## Troubleshooting

### FFmpeg Not Found
If you get an error about FFmpeg, ensure it's installed and in your PATH.

### API Key Error
Make sure your API key is valid and has the necessary permissions.

### Memory Issues with Large Files
The script handles large files efficiently through the Files API, but ensure you have sufficient disk space for temporary files when trimming.

### Unsupported Format
Convert your audio to a supported format using FFmpeg:
```bash
ffmpeg -i input.webm -acodec mp3 output.mp3
```

## License

Apache License - See LICENSE file for details

Always check permission for downloading your audio file

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
```

This solution provides:

1. **Full-featured script** with all requested functionality
2. **Token counting** for monitoring API usage
3. **Files API integration** for handling large files (>20MB)
4. **Audio trimming** with MM:SS format support
5. **Summary generation** option
6. **Comprehensive help** via `--help` flag
7. **Clean error handling** and user feedback
8. **Detailed README** with installation instructions and examples
9. **Support for multiple audio formats** beyond just MP3

The script is production-ready and includes proper cleanup, error handling, and user-friendly output messages.
