#!/usr/bin/env python3
"""
MP3 to Text Converter using Google Gemini API
Converts audio files to text with optional summarization
Uses Gemini 2.5 Flash model
"""
import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional, Any
import google.generativeai as genai
from google.api_core import exceptions as gcp_exceptions
from pydub import AudioSegment
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import tempfile
import re
import shutil

# Constants
SUPPORTED_FORMATS = ['.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg', '.aiff']
MAX_FILE_SIZE_MB = 20
MODEL_NAME = 'gemini-2.5-flash'

def sanitize_filename(name: str) -> str:
    """Sanitize text for safe filesystem usage."""
    sanitized = re.sub(r'[^\w\s.\-]', '_', name or '')
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized[:180] or "youtube_audio"

def download_youtube_audio(url: str, target_path: Optional[Path] = None) -> Path:
    """Download audio from YouTube and export it as an MP3 file using yt-dlp workflow."""
    print(f"Preparing YouTube audio download: {url}")
    with tempfile.TemporaryDirectory(prefix="yt_audio_") as temp_dir:
        temp_dir_path = Path(temp_dir)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(temp_dir_path / "%(id)s.%(ext)s"),
            "quiet": True,
            "noprogress": True,
            "ignoreerrors": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except DownloadError as e:
            raise RuntimeError(f"Failed to download YouTube audio: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error downloading YouTube audio: {e}") from e

        title = info.get("title") or info.get("id") or "youtube_audio"
        safe_title = sanitize_filename(title)

        if target_path:
            target_path = Path(target_path)
            if target_path.exists() and target_path.is_dir():
                target_path = target_path / f"{safe_title}.mp3"
            elif target_path.suffix.lower() != ".mp3":
                target_path = target_path.with_suffix(".mp3")
        else:
            target_path = Path("downloads") / f"{safe_title}.mp3"

        target_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded_files = sorted(temp_dir_path.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not downloaded_files:
            raise RuntimeError("yt-dlp did not produce an MP3 file. Ensure ffmpeg is installed and accessible.")

        downloaded_file = downloaded_files[0]
        shutil.move(str(downloaded_file), target_path)
        print(f"Downloaded MP3 via yt-dlp: {target_path}")

    return target_path

class AudioTranscriber:
    def __init__(self, api_key: str):
        """Initialize the transcriber with Gemini API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(MODEL_NAME)
        print(f"Initialized with model: {MODEL_NAME}")

    def check_api_enabled(self):
        """Check if the Generative Language API is enabled."""
        try:
            # Attempt a simple API call to verify access
            self.model.count_tokens("Test")
            return True
        except gcp_exceptions.PermissionDenied as e:
            if "API has not been enabled" in str(e):
                print(f"Error: The Generative Language API is not enabled for your Google Cloud project.")
                print("Please enable it using one of the following methods:")
                print("1. Google Cloud Console:")
                print("   - Go to https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
                print("   - Select your project and click 'Enable'")
                print("2. gcloud CLI:")
                print("   - Run: gcloud services enable generativelanguage.googleapis.com")
                print("Ensure your API key has the necessary permissions and is associated with the correct project.")
                return False
            raise e
        except Exception as e:
            print(f"Error checking API status: {e}")
            return False

    def parse_time(self, time_str: str) -> int:
        """Convert MM:SS format to milliseconds."""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                raise ValueError
            minutes = int(parts[0])
            seconds = int(parts[1])
            return (minutes * 60 + seconds) * 1000
        except (ValueError, IndexError):
            raise ValueError(f"Invalid time format: {time_str}. Use MM:SS format.")

    def trim_audio(self, input_file: str, start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> str:
        """Trim audio file if start/end times are specified."""
        if not start_time and not end_time:
            return input_file
        print(f"Trimming audio file...")
        audio = AudioSegment.from_file(input_file)
        start_ms = self.parse_time(start_time) if start_time else 0
        end_ms = self.parse_time(end_time) if end_time else len(audio)
        if start_ms >= end_ms:
            raise ValueError("Start time must be before end time")
        if start_ms > len(audio):
            raise ValueError("Start time exceeds audio duration")
        trimmed = audio[start_ms:end_ms]
        # Save trimmed audio to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        trimmed.export(temp_file.name, format='mp3')
        temp_file.close()
        duration = (end_ms - start_ms) / 1000
        print(f"Audio trimmed: {duration:.1f} seconds")
        return temp_file.name

    def upload_file(self, file_path: str) -> Any:
        """Upload file to Gemini Files API."""
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"Uploading file: {os.path.basename(file_path)} ({file_size_mb:.2f} MB)")
        # Upload the file
        uploaded_file = genai.upload_file(
            path=file_path,
            display_name=os.path.basename(file_path)
        )
        # Wait for file processing
        print("Waiting for file processing...")
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
        if uploaded_file.state.name != "ACTIVE":
            raise Exception(f"File upload failed with state: {uploaded_file.state.name}")
        print(f"File uploaded successfully: {uploaded_file.uri}")
        return uploaded_file

    def process_inline(self, file_path: str) -> dict:
        """Process small audio files inline."""
        print("Processing audio inline...")
        mime_types = {
            '.mp3': 'audio/mp3',
            '.wav': 'audio/wav',
            '.aac': 'audio/aac',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.aiff': 'audio/aiff'
        }
        ext = Path(file_path).suffix.lower()
        mime_type = mime_types.get(ext, 'audio/mp3')
        with open(file_path, 'rb') as f:
            audio_bytes = f.read()
        # Return a dictionary for inline audio data
        return {
            'inline_data': {
                'mime_type': mime_type,
                'data': audio_bytes
            }
        }

    def count_tokens(self, content) -> int:
        """Count tokens in the input."""
        try:
            response = self.model.count_tokens(content)
            return response.total_tokens
        except Exception as e:
            print(f"Warning: Could not count tokens: {e}")
            return 0

    def transcribe(self, audio_content,
                   system_instruction: Optional[str] = None,
                   use_timestamps: bool = False,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> str:
        """Transcribe audio file to text."""
        # Build the prompt
        if use_timestamps and start_time and end_time:
            prompt = f"Provide a transcript of the speech from {start_time} to {end_time}."
        else:
            prompt = "Generate a transcript of the speech. Include all spoken content accurately."
        contents = [prompt, audio_content]
        # Count and display input tokens
        token_count = self.count_tokens(contents)
        if token_count > 0:
            print(f"Input tokens: {token_count}")
        print(f"Transcribing audio using {MODEL_NAME}...")
        # Configure generation
        generation_config = genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
        )
        # Use system instruction if provided
        if system_instruction:
            model = genai.GenerativeModel(
                MODEL_NAME,
                system_instruction=system_instruction
            )
        else:
            model = self.model
        response = model.generate_content(
            contents,
            generation_config=generation_config
        )
        return response.text

    def summarize(self, text: str) -> str:
        """Create a summary of the transcribed text."""
        prompt = f"""Please provide a concise summary of the following text.
        Include the main points and key information.
        Text to summarize:
        {text}
        """
        # Count and display input tokens
        token_count = self.count_tokens(prompt)
        if token_count > 0:
            print(f"Summary input tokens: {token_count}")
        print(f"Generating summary using {MODEL_NAME}...")
        generation_config = genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        )
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return response.text

    def cleanup_file(self, file: Any):
        """Delete uploaded file from Gemini."""
        try:
            genai.delete_file(file.name)
            print(f"Cleaned up uploaded file: {file.name}")
        except Exception as e:
            print(f"Warning: Could not delete uploaded file: {e}")

def validate_file(file_path: str) -> float:
    """Validate input file and return size in MB."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {file_path}")
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format. Supported: {', '.join(SUPPORTED_FORMATS)}")
    # Return file size in MB
    return path.stat().st_size / (1024 * 1024)

def main():
    parser = argparse.ArgumentParser(
        description=f'Convert audio files to text using Google Gemini API ({MODEL_NAME})',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s input.mp3 output.txt
  %(prog)s input.mp3 output.txt --summary summary.txt
  %(prog)s input.mp3 output.txt --start 01:30 --end 05:45
  %(prog)s input.mp3 output.txt --inline # For small files (<20MB)
  %(prog)s transcript.txt --youtube-url https://youtu.be/VIDEO_ID --youtube-output downloads/video.mp3
Model: {MODEL_NAME}
Supported formats: MP3, WAV, AAC, FLAC, M4A, OGG, AIFF
Max audio length: 9.5 hours
        """
    )
    parser.add_argument('input', nargs='?', help='Input audio file path (or target MP3 path when using --youtube-url)')
    parser.add_argument('output', help='Output text file path')
    parser.add_argument('--api-key',
                        help='Gemini API key (or set GEMINI_API_KEY env variable)')
    parser.add_argument('--youtube-url', metavar='URL',
                        help='Download audio from a YouTube URL and use it as the input source')
    parser.add_argument('--youtube-output',
                        help='Optional path or directory for the downloaded MP3 (defaults to ./downloads/<title>.mp3)')
    parser.add_argument('--summary', metavar='FILE',
                        help='Generate summary and save to specified file')
    parser.add_argument('--start', metavar='MM:SS',
                        help='Start time for audio trimming')
    parser.add_argument('--end', metavar='MM:SS',
                        help='End time for audio trimming')
    parser.add_argument('--system-instruction',
                        help='System instruction for the model')
    parser.add_argument('--inline', action='store_true',
                        help='Process audio inline (for files <20MB)')
    parser.add_argument('--keep-uploaded', action='store_true',
                        help='Keep uploaded file in Gemini (don\'t delete after processing)')
    parser.add_argument('--use-timestamps', action='store_true',
                        help='Use timestamp-based transcription (requires --start and --end)')
    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: Gemini API key required. Use --api-key or set GEMINI_API_KEY environment variable.")
        sys.exit(1)

    temp_file = None
    uploaded_file = None
    downloaded_mp3 = None
    try:
        audio_file_path: Optional[str] = args.input
        if args.youtube_url:
            target_candidate: Optional[Path] = None
            if args.youtube_output:
                target_candidate = Path(args.youtube_output)
            elif audio_file_path:
                target_candidate = Path(audio_file_path)
            downloaded_mp3 = download_youtube_audio(args.youtube_url, target_candidate)
            audio_file_path = str(downloaded_mp3)
            print(f"Using downloaded MP3 as input: {audio_file_path}")
        if not audio_file_path:
            print("Error: input audio file path required. Provide a local file or use --youtube-url.")
            sys.exit(1)
        audio_file_path = str(audio_file_path)
        file_size_mb = validate_file(audio_file_path)
        print(f"Processing: {audio_file_path} ({file_size_mb:.2f} MB)")
        transcriber = AudioTranscriber(api_key)
        if not transcriber.check_api_enabled():
            sys.exit(1)
        if args.start or args.end:
            if not args.use_timestamps:
                temp_file = transcriber.trim_audio(audio_file_path, args.start, args.end)
                audio_file_path = temp_file
                file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        # Process audio based on size and preference
        if args.inline or file_size_mb < MAX_FILE_SIZE_MB:
            if file_size_mb >= MAX_FILE_SIZE_MB:
                print(f"Warning: File size ({file_size_mb:.2f} MB) exceeds limit for inline processing.")
                print("Switching to file upload method...")
                audio_content = transcriber.upload_file(audio_file_path)
                uploaded_file = audio_content
            else:
                audio_content = transcriber.process_inline(audio_file_path)
        else:
            # Upload file to Gemini
            audio_content = transcriber.upload_file(audio_file_path)
            uploaded_file = audio_content
        # Transcribe audio
        transcription = transcriber.transcribe(
            audio_content,
            system_instruction=args.system_instruction,
            use_timestamps=args.use_timestamps,
            start_time=args.start,
            end_time=args.end
        )
        # Save transcription
        print(f"Saving transcription to: {args.output}")
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(transcription)
        print(f"Transcription saved successfully!")
        print(f"Output length: {len(transcription)} characters")
        # Generate summary if requested
        if args.summary:
            summary = transcriber.summarize(transcription)
            print(f"Saving summary to: {args.summary}")
            summary_path = Path(args.summary)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            with open(args.summary, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"Summary saved successfully!")
            print(f"Summary length: {len(summary)} characters")
        # Cleanup
        if uploaded_file and not args.keep_uploaded:
            transcriber.cleanup_file(uploaded_file)
        print(f"\nProcess completed successfully using {MODEL_NAME}!")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Clean up temporary trimmed file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print("Cleaned up temporary trimmed file")
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {e}")

if __name__ == "__main__":
    main()
