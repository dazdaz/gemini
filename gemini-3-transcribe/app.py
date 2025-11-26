#!/usr/bin/env python3
"""
Flask Web Application for Gemini Transcribe
Uses Google Gemini API for audio transcription
Supports multiple models for cost optimization
"""
import os
import sys
import uuid
import base64
import warnings
import tempfile
import traceback
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify

# Suppress FutureWarning for Python version deprecated warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.api_core')

from gemini_transcribe_cli import (
    AudioTranscriber, download_youtube_audio, validate_file, 
    MAX_FILE_SIZE_MB, get_audio_duration_seconds, AVAILABLE_MODELS, DEFAULT_MODEL
)

app = Flask(__name__)

# Get API key from environment (supports .env file)
API_KEY = os.environ.get('GEMINI_API_KEY')

# Web app inline limit (smaller than CLI due to request size limits)
WEB_INLINE_LIMIT_MB = 20


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL)


@app.route('/download-audio', methods=['POST'])
def download_audio():
    """Handle audio-only download request (no transcription)."""
    print("\n" + "="*50)
    print("New audio download request received")
    print("="*50)
    
    data = request.get_json()
    youtube_url = data.get('youtube_url', '').strip()
    
    print(f"YouTube URL: {youtube_url}")

    if not youtube_url:
        return jsonify({
            'success': False,
            'error': 'Please provide a YouTube URL'
        }), 400

    # Validate URL format
    if not ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
        return jsonify({
            'success': False,
            'error': 'Invalid YouTube URL. Please provide a valid YouTube video URL.'
        }), 400

    try:
        # Create unique session directory
        session_id = str(uuid.uuid4())[:8]
        print(f"Session ID: {session_id}")
        
        with tempfile.TemporaryDirectory(prefix=f"yt_audio_{session_id}_") as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Temp directory: {temp_path}")
            
            # Download YouTube audio
            print("Downloading YouTube audio...")
            mp3_path = download_youtube_audio(youtube_url, temp_path)
            print(f"Downloaded: {mp3_path}")
            
            # Read audio file
            print("Reading audio file for download...")
            with open(mp3_path, 'rb') as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            print(f"Audio encoded: {len(audio_base64)} characters")
            
            response_data = {
                'success': True,
                'video_title': mp3_path.stem,
                'audio_base64': audio_base64
            }
            
            print("Audio download request completed successfully!")
            return jsonify(response_data)

    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Handle transcription request."""
    print("\n" + "="*50)
    print("New transcription request received")
    print("="*50)
    
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        return jsonify({
            'success': False,
            'error': 'GEMINI_API_KEY environment variable not set. Create a .env file with GEMINI_API_KEY=your_key'
        }), 500

    data = request.get_json()
    youtube_url = data.get('youtube_url', '').strip()
    generate_summary = data.get('generate_summary', False)
    save_audio = data.get('save_audio', False)
    model_name = data.get('model', DEFAULT_MODEL)
    
    # Validate model
    if model_name not in AVAILABLE_MODELS:
        model_name = DEFAULT_MODEL
    
    print(f"YouTube URL: {youtube_url}")
    print(f"Model: {model_name}")
    print(f"Generate summary: {generate_summary}")
    print(f"Save audio: {save_audio}")

    if not youtube_url:
        return jsonify({
            'success': False,
            'error': 'Please provide a YouTube URL'
        }), 400

    # Validate URL format
    if not ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
        return jsonify({
            'success': False,
            'error': 'Invalid YouTube URL. Please provide a valid YouTube video URL.'
        }), 400

    try:
        # Create unique session directory
        session_id = str(uuid.uuid4())[:8]
        print(f"Session ID: {session_id}")
        
        total_cost = 0.0
        
        with tempfile.TemporaryDirectory(prefix=f"yt_transcribe_{session_id}_") as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Temp directory: {temp_path}")
            
            # Download YouTube audio
            print("Downloading YouTube audio...")
            mp3_path = download_youtube_audio(youtube_url, temp_path)
            print(f"Downloaded: {mp3_path}")
            
            # Validate file
            file_size_mb = validate_file(str(mp3_path))
            print(f"File size: {file_size_mb:.2f} MB")
            
            # Get audio duration for cost estimation
            audio_duration = get_audio_duration_seconds(str(mp3_path))
            print(f"Audio duration: {audio_duration:.1f} seconds ({audio_duration/60:.1f} minutes)")
            
            # Read audio file if save_audio is requested
            audio_base64 = None
            if save_audio:
                print("Reading audio file for download...")
                with open(mp3_path, 'rb') as f:
                    audio_bytes = f.read()
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                print(f"Audio encoded: {len(audio_base64)} characters")
            
            # Initialize transcriber with selected model
            print(f"Initializing transcriber with model: {model_name}...")
            transcriber = AudioTranscriber(API_KEY, model_name)
            
            # Check API is enabled
            print("Checking API status...")
            if not transcriber.check_api_enabled():
                return jsonify({
                    'success': False,
                    'error': 'Gemini API is not enabled. Please check your API key and project settings.'
                }), 500
            
            # Process audio - use inline for files up to 20MB, upload for larger
            uploaded_file = None
            if file_size_mb <= WEB_INLINE_LIMIT_MB:
                print(f"Processing audio inline ({file_size_mb:.2f} MB <= {WEB_INLINE_LIMIT_MB} MB limit)...")
                audio_content = transcriber.process_inline(str(mp3_path))
            else:
                print(f"File size ({file_size_mb:.2f} MB) exceeds inline limit ({WEB_INLINE_LIMIT_MB} MB)")
                print("Using Files API upload...")
                audio_content = transcriber.upload_file(str(mp3_path))
                uploaded_file = audio_content
            
            # Transcribe
            print("Starting transcription...")
            transcription = transcriber.transcribe(
                audio_content,
                audio_duration_seconds=audio_duration
            )
            print(f"Transcription complete: {len(transcription)} characters")
            
            # Get transcription cost
            usage = transcriber.get_last_usage()
            total_cost += usage.get('total_cost', 0)
            
            # Generate summary if requested
            summary = None
            if generate_summary:
                print("Generating summary...")
                summary, summary_usage = transcriber.summarize(transcription)
                total_cost += summary_usage.get('total_cost', 0)
                print(f"Summary complete: {len(summary)} characters")
            
            # Cleanup uploaded file
            if uploaded_file:
                transcriber.cleanup_file(uploaded_file)
            
            response_data = {
                'success': True,
                'transcription': transcription,
                'video_title': mp3_path.stem,
                'audio_duration_seconds': audio_duration,
                'estimated_cost': round(total_cost, 4),
                'model_used': model_name
            }
            
            if summary:
                response_data['summary'] = summary
            
            if audio_base64:
                response_data['audio_base64'] = audio_base64
            
            print(f"Request completed successfully!")
            print(f"Model: {model_name}")
            print(f"Total estimated cost: ${total_cost:.4f}")
            return jsonify(response_data)

    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/health')
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("\n" + "="*60)
    print("GEMINI TRANSCRIBE - Development Server")
    print("="*60)
    print(f"\nServer URL: http://localhost:{port}")
    print(f"Default model: {DEFAULT_MODEL}")
    print("\nAvailable models:")
    for model_id, info in AVAILABLE_MODELS.items():
        default = " (default)" if model_id == DEFAULT_MODEL else ""
        print(f"  - {model_id}: {info['name']}{default}")
    print("\nFor production, use:")
    print("  gunicorn --bind :8080 --workers 1 --threads 8 --timeout 600 app:app")
    print("="*60 + "\n")
    
    if not API_KEY:
        print("⚠️  WARNING: GEMINI_API_KEY not set!")
        print("   Create a .env file with: GEMINI_API_KEY=your_api_key")
        print()
    else:
        print(f"✓ API Key loaded (ends with ...{API_KEY[-4:]})")
        print()
    
    app.run(host='0.0.0.0', port=port, debug=True)
