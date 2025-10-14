#!/usr/bin/env python3
"""
Chirp 2 Live Transcription with Gemini Translation - Web Version
Real-time audio transcription using Google Cloud Speech-to-Text V2 (Chirp)
with live translation via Gemini API and customizable TTS voices
"""

import os
import sys
import logging
import base64
from datetime import datetime
from typing import Optional, Dict
import queue
import struct
import io

import google.auth
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud import texttospeech
from google.api_core.exceptions import NotFound
import google.generativeai as genai
from flask import Flask, render_template, jsonify, send_file, request as flask_request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

SAMPLE_RATE = 16000
CHANNELS = 1
LOCATION = "us-central1"
RECOGNIZER_ID = "chirp-recognizer-v2"
MODEL = "chirp_2"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)
socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    async_mode='threading', 
                    ping_timeout=120, 
                    ping_interval=25,
                    logger=False,
                    engineio_logger=False)

speech_client: Optional[SpeechClient] = None
tts_client: Optional[texttospeech.TextToSpeechClient] = None
gemini_translator: Optional['GeminiTranslator'] = None
recognizer_name: Optional[str] = None
sessions: Dict[str, Dict] = {}

# ============================================================================
# STARTUP CHECKS
# ============================================================================

def startup_checks() -> tuple[str, str]:
    """Perform comprehensive startup checks for all required services and credentials."""
    print("=" * 80)
    print("CHIRP 2 LIVE TRANSCRIPTION - WEB VERSION STARTUP CHECK")
    print("=" * 80)
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("‚úó GEMINI_API_KEY environment variable not set")
        raise RuntimeError("Missing GEMINI_API_KEY")
    logger.info("‚úì GEMINI_API_KEY is set")
    
    try:
        credentials, project_from_creds = google.auth.default()
        logger.info("‚úì Google Cloud credentials found")
    except Exception as e:
        logger.error(f"‚úó Google Cloud credentials error: {e}")
        raise RuntimeError("Google Cloud credentials not found") from e
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or project_from_creds
    if not project_id:
        logger.error("‚úó No Google Cloud Project ID found")
        raise RuntimeError("Missing project ID")
    
    logger.info(f"‚úì Using Google Cloud Project ID: {project_id}")
    logger.info(f"‚úì Using location: {LOCATION}")
    
    return project_id, gemini_api_key


def get_or_create_recognizer(project_id: str, client: SpeechClient) -> str:
    """Get existing recognizer or create a new one."""
    recognizer_name = f"projects/{project_id}/locations/{LOCATION}/recognizers/{RECOGNIZER_ID}"
    
    try:
        existing_recognizer = client.get_recognizer(name=recognizer_name)
        logger.info(f"‚úì Using existing recognizer")
        return recognizer_name
    except NotFound:
        logger.info("Recognizer not found, creating new one")
    except Exception as e:
        logger.warning(f"Error checking for recognizer: {e}")
    
    try:
        logger.info(f"Creating new Chirp recognizer: {RECOGNIZER_ID}")
        
        request = cloud_speech.CreateRecognizerRequest(
            parent=f"projects/{project_id}/locations/{LOCATION}",
            recognizer_id=RECOGNIZER_ID,
            recognizer=cloud_speech.Recognizer(
                model=MODEL,
                language_codes=["en-US"],
                default_recognition_config=cloud_speech.RecognitionConfig(
                    explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                        encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                        sample_rate_hertz=SAMPLE_RATE,
                        audio_channel_count=CHANNELS,
                    ),
                    features=cloud_speech.RecognitionFeatures(
                        enable_automatic_punctuation=True,
                        enable_word_time_offsets=False,
                    ),
                ),
            ),
        )
        
        operation = client.create_recognizer(request=request)
        recognizer = operation.result(timeout=180)
        
        logger.info(f"‚úì Recognizer created successfully: {recognizer.name}")
        return recognizer.name
        
    except Exception as e:
        logger.error(f"‚úó Failed to create recognizer: {e}")
        raise RuntimeError(f"Could not create recognizer: {str(e)}") from e


# ============================================================================
# GEMINI TRANSLATION
# ============================================================================

class GeminiTranslator:
    """Handles translation using Gemini API"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("‚úì Gemini translator initialized")
    
    def translate(self, text: str, target_language: str) -> str:
        """Translate text to target language"""
        if not text.strip():
            return ""
        
        try:
            prompt = f"Translate the following text to {target_language}. Only return the translation, nothing else:\n\n{text}"
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return f"[Translation error: {e}]"


# ============================================================================
# TEXT-TO-SPEECH
# ============================================================================

# Language code mapping for Google TTS
TTS_LANGUAGE_MAP = {
    'Spanish': 'es-ES',
    'English': 'en-US',
    'French': 'fr-FR',
    'German': 'de-DE',
    'Italian': 'it-IT',
    'Portuguese': 'pt-BR',
    'Japanese': 'ja-JP',
    'Korean': 'ko-KR',
    'Chinese': 'zh-CN',
    'Arabic': 'ar-XA',
    'Danish': 'da-DK',
    'Greek': 'el-GR',
    'Indonesian': 'id-ID',
    'Polish': 'pl-PL',
    'Thai': 'th-TH',
    'Turkish': 'tr-TR',
    'Filipino': 'fil-PH',
    'Cebuano': 'ceb-PH'
}

def generate_speech(text: str, target_language: str, voice_gender: str = 'NEUTRAL') -> bytes:
    """Generate speech audio from text using Google Cloud TTS
    
    Args:
        text: Text to convert to speech
        target_language: Target language name
        voice_gender: Voice gender - 'MALE', 'FEMALE', or 'NEUTRAL'
    """
    try:
        # Map the target language to TTS language code
        language_code = TTS_LANGUAGE_MAP.get(target_language, 'en-US')
        
        # Map voice gender string to enum
        gender_map = {
            'MALE': texttospeech.SsmlVoiceGender.MALE,
            'FEMALE': texttospeech.SsmlVoiceGender.FEMALE,
            'NEUTRAL': texttospeech.SsmlVoiceGender.NEUTRAL
        }
        
        ssml_gender = gender_map.get(voice_gender.upper(), texttospeech.SsmlVoiceGender.NEUTRAL)
        
        # Set up the text input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=ssml_gender
        )
        
        # Select the audio format
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        # Perform the TTS request
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        logger.info(f"TTS generated: {len(text)} chars, {language_code}, {voice_gender}")
        return response.audio_content
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise


# ============================================================================
# LANGUAGE MAPPING
# ============================================================================

LANGUAGE_NAMES = {
    'ar-AE': 'Arabic',
    'zh-CN': 'Chinese (Simplified)',
    'da-DK': 'Danish',
    'en-GB': 'English (UK)',
    'en-US': 'English (US)',
    'fr-FR': 'French',
    'de-DE': 'German',
    'el-GR': 'Greek',
    'id-ID': 'Indonesian',
    'it-IT': 'Italian',
    'ja-JP': 'Japanese',
    'ko-KR': 'Korean',
    'pl-PL': 'Polish',
    'pt-BR': 'Portuguese (Brazil)',
    'es-MX': 'Spanish (Mexico)',
    'es-ES': 'Spanish (Spain)',
    'th-TH': 'Thai',
    'tr-TR': 'Turkish'
}

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = flask_request.sid
    logger.info(f"Client connected: {session_id}")
    
    join_room(session_id)
    
    sessions[session_id] = {
        'active': False,
        'audio_queue': queue.Queue(),
        'audio_chunks': [],
        'original_text': '',
        'translated_text': '',
        'source_language': 'en-US',
        'target_language': 'Spanish',
        'stream_active': False,
        'stream_thread': None,
        'pending_audio': [],
        'show_timestamps': False,
        'tts_audio': None,
        'voice_gender': 'NEUTRAL'  # NEW: Default voice gender
    }
    
    emit('connected', {'session_id': session_id})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = flask_request.sid
    logger.info(f"Client disconnected: {session_id}")
    
    if session_id in sessions:
        sessions[session_id]['active'] = False
        sessions[session_id]['stream_active'] = False
        
        thread = sessions[session_id].get('stream_thread')
        if thread and thread.is_alive():
            thread.join(timeout=2)
        
        leave_room(session_id)
        del sessions[session_id]


@socketio.on('start_session')
def handle_start_session(data):
    """Start a new transcription session"""
    session_id = flask_request.sid
    
    try:
        source_language = data.get('source_language', 'en-US')
        target_language = data.get('target_language', 'Spanish')
        show_timestamps = data.get('show_timestamps', False)
        voice_gender = data.get('voice_gender', 'NEUTRAL')  # NEW: Get voice gender
        
        logger.info(f"Starting session {session_id}: {source_language} -> {target_language} (timestamps: {show_timestamps}, voice: {voice_gender})")
        
        sessions[session_id].update({
            'active': True,
            'source_language': source_language,
            'target_language': target_language,
            'show_timestamps': show_timestamps,
            'voice_gender': voice_gender,  # NEW: Store voice gender
            'audio_queue': queue.Queue(),
            'audio_chunks': [],
            'original_text': '',
            'translated_text': '',
            'stream_active': True,
            'pending_audio': [],
            'tts_audio': None
        })
        
        thread = threading.Thread(target=streaming_transcribe, args=(session_id,), daemon=True)
        sessions[session_id]['stream_thread'] = thread
        thread.start()
        
        time.sleep(0.5)
        
        pending = sessions[session_id].get('pending_audio', [])
        for audio_bytes in pending:
            sessions[session_id]['audio_queue'].put(audio_bytes)
        sessions[session_id]['pending_audio'] = []
        
        emit('session_started', {
            'source_language': source_language,
            'target_language': target_language,
            'show_timestamps': show_timestamps,
            'voice_gender': voice_gender  # NEW: Confirm voice gender
        })
        
    except Exception as e:
        logger.error(f"Error starting session: {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('audio_data')
def handle_audio_data(data):
    """Handle incoming audio data from client"""
    session_id = flask_request.sid
    
    if session_id not in sessions:
        return
    
    try:
        audio_bytes = base64.b64decode(data['audio'])
        sessions[session_id]['audio_chunks'].append(audio_bytes)
        
        if sessions[session_id].get('stream_active', False):
            sessions[session_id]['audio_queue'].put(audio_bytes)
        else:
            sessions[session_id].setdefault('pending_audio', []).append(audio_bytes)
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        emit('error', {'message': f'Audio processing error: {str(e)}'})


def streaming_transcribe(session_id: str):
    """Background thread for streaming transcription"""
    
    if session_id not in sessions:
        logger.error(f"Session {session_id} not found")
        return
    
    session = sessions[session_id]
    source_language = session['source_language']
    target_language = session['target_language']
    show_timestamps = session.get('show_timestamps', False)
    
    logger.info(f"Starting streaming transcription for session {session_id}")
    logger.info(f"Source: {source_language}, Target: {target_language}, Timestamps: {show_timestamps}")
    
    try:
        config = cloud_speech.StreamingRecognitionConfig(
            config=cloud_speech.RecognitionConfig(
                explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                    encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=SAMPLE_RATE,
                    audio_channel_count=CHANNELS,
                ),
                language_codes=[source_language],
                model=MODEL,
                features=cloud_speech.RecognitionFeatures(
                    enable_automatic_punctuation=True,
                ),
            ),
            streaming_features=cloud_speech.StreamingRecognitionFeatures(
                interim_results=True,
            ),
        )
        
        def request_generator():
            yield cloud_speech.StreamingRecognizeRequest(
                recognizer=recognizer_name,
                streaming_config=config,
            )
            
            while session.get('stream_active', False):
                try:
                    audio_chunk = session['audio_queue'].get(timeout=0.1)
                    yield cloud_speech.StreamingRecognizeRequest(audio=audio_chunk)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in request generator: {e}")
                    break
        
        responses = speech_client.streaming_recognize(request_generator())
        
        for response in responses:
            if not session.get('stream_active', False):
                break
                
            for result in response.results:
                if not result.alternatives:
                    continue
                
                transcript = result.alternatives[0].transcript
                is_final = result.is_final
                confidence = result.alternatives[0].confidence if is_final else 0.0
                
                result_end_offset = None
                if show_timestamps and hasattr(result, 'result_end_offset'):
                    result_end_offset = result.result_end_offset.total_seconds()
                
                if is_final:
                    session['original_text'] += transcript + ' '
                    
                    logger.info(f"Translating '{transcript}' to {target_language}")
                    translation = gemini_translator.translate(transcript, target_language)
                    logger.info(f"Translation result: {translation}")
                    
                    session['translated_text'] += translation + ' '
                    
                    emit_data = {
                        'original': transcript,
                        'translation': translation,
                        'is_final': True,
                        'confidence': confidence,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if result_end_offset is not None:
                        emit_data['chirp_timestamp'] = result_end_offset
                    
                    socketio.emit('transcription', emit_data, room=session_id)
                else:
                    emit_data = {
                        'original': transcript,
                        'is_final': False,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if result_end_offset is not None:
                        emit_data['chirp_timestamp'] = result_end_offset
                    
                    socketio.emit('transcription', emit_data, room=session_id)
                    
    except Exception as e:
        logger.error(f"Error in streaming_transcribe: {e}", exc_info=True)
        socketio.emit('error', {'message': str(e)}, room=session_id)


@socketio.on('stop_session')
def handle_stop_session():
    """Stop transcription session"""
    session_id = flask_request.sid
    
    if session_id in sessions:
        sessions[session_id]['stream_active'] = False
        time.sleep(1.0)
        sessions[session_id]['active'] = False
    
    emit('session_stopped', {'message': 'Session stopped'})
    logger.info(f"Stopped session: {session_id}")


@socketio.on('request_tts')
def handle_request_tts(data):
    """Handle text-to-speech request"""
    session_id = flask_request.sid
    text = data.get('text', '')
    target_language = data.get('target_language', 'Spanish')
    voice_gender = data.get('voice_gender', 'NEUTRAL')  # NEW: Get voice gender
    
    if not text.strip():
        logger.warning("TTS requested with empty text")
        return
    
    try:
        logger.info(f"TTS requested for session {session_id}: {text[:50]}... in {target_language} ({voice_gender})")
        
        # Generate speech with specified voice gender
        audio_content = generate_speech(text, target_language, voice_gender)
        
        # Store the TTS audio in the session
        if session_id in sessions:
            sessions[session_id]['tts_audio'] = audio_content
        
        # Convert to base64 for transmission
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        # Send to client
        emit('tts_audio', {
            'audio': audio_base64,
            'format': 'mp3',
            'voice_gender': voice_gender  # NEW: Include voice info
        }, room=session_id)
        
        logger.info(f"TTS audio sent successfully ({len(audio_content)} bytes, {voice_gender})")
        
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        emit('error', {'message': f'Text-to-speech error: {str(e)}'}, room=session_id)


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'speech_client': speech_client is not None,
        'tts_client': tts_client is not None,
        'translator': gemini_translator is not None,
        'recognizer': recognizer_name is not None,
        'active_sessions': len([s for s in sessions.values() if s.get('active', False)])
    })


@app.route('/api/download/<session_id>/audio')
def download_audio(session_id):
    """Download recorded audio as WAV"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    audio_chunks = sessions[session_id].get('audio_chunks', [])
    if not audio_chunks:
        return jsonify({'error': 'No audio recorded'}), 404
    
    wav_data = create_wav_file(audio_chunks)
    
    return send_file(
        io.BytesIO(wav_data),
        mimetype='audio/wav',
        as_attachment=True,
        download_name=f'recording_{session_id}.wav'
    )


@app.route('/api/download/<session_id>/text')
def download_text(session_id):
    """Download transcription as text file"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = sessions[session_id]
    
    text_content = f"""Live Transcription Session
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Source Language: {session.get('source_language', 'Unknown')}
Target Language: {session.get('target_language', 'Unknown')}

ORIGINAL TEXT:
{session.get('original_text', '')}

TRANSLATION:
{session.get('translated_text', '')}
"""
    
    return send_file(
        io.BytesIO(text_content.encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'transcription_{session_id}.txt'
    )


@app.route('/api/download/<session_id>/translation')
def download_translation(session_id):
    """Download translation text only"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = sessions[session_id]
    translation_text = session.get('translated_text', '')
    
    if not translation_text.strip():
        return jsonify({'error': 'No translation available'}), 404
    
    return send_file(
        io.BytesIO(translation_text.encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'translation_{session_id}.txt'
    )


@app.route('/api/download/<session_id>/tts')
def download_tts_audio(session_id):
    """Download TTS audio as MP3"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    tts_audio = sessions[session_id].get('tts_audio')
    if not tts_audio:
        return jsonify({'error': 'No TTS audio available'}), 404
    
    return send_file(
        io.BytesIO(tts_audio),
        mimetype='audio/mpeg',
        as_attachment=True,
        download_name=f'translation_audio_{session_id}.mp3'
    )


def create_wav_file(audio_chunks):
    """Create WAV file from audio chunks (LINEAR16 PCM)"""
    audio_data = b''.join(audio_chunks)
    
    sample_rate = SAMPLE_RATE
    num_channels = CHANNELS
    bits_per_sample = 16
    
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(audio_data)
    
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size
    )
    
    return header + audio_data


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

def initialize_services():
    """Initialize all services on startup"""
    global speech_client, tts_client, gemini_translator, recognizer_name
    
    try:
        project_id, gemini_api_key = startup_checks()
        
        from google.api_core.client_options import ClientOptions
        
        client_options = ClientOptions(
            api_endpoint=f"{LOCATION}-speech.googleapis.com"
        )
        
        speech_client = SpeechClient(client_options=client_options)
        logger.info(f"‚úì Speech client initialized")
        
        tts_client = texttospeech.TextToSpeechClient()
        logger.info(f"‚úì Text-to-Speech client initialized")
        
        recognizer_name = get_or_create_recognizer(project_id, speech_client)
        gemini_translator = GeminiTranslator(gemini_api_key)
        
        print("\n" + "=" * 80)
        print("‚úì ALL SYSTEMS READY")
        print("=" * 80)
        print(f"Server: http://localhost:5000")
        print(f"Location: {LOCATION}")
        print(f"Model: {MODEL}")
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"‚úó Initialization failed: {e}", exc_info=True)
        sys.exit(1)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    initialize_services()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

