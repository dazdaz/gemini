// Initialize Socket.IO connection
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5
});

// DOM elements
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const playbackBtn = document.getElementById('playback-btn');
const downloadAudioBtn = document.getElementById('download-audio-btn');
const downloadTextBtn = document.getElementById('download-text-btn');
const speakTranslationBtn = document.getElementById('speak-translation-btn');
const sourceLanguage = document.getElementById('source-language');
const targetLanguage = document.getElementById('target-language');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const selectedLanguages = document.getElementById('selected-languages');
const playbackAudio = document.getElementById('playback-audio');
const originalDisplay = document.getElementById('original-display');
const translationDisplay = document.getElementById('translation-display');

// State
let isRecording = false;
let audioContext = null;
let sessionId = null;
let audioChunks = [];
let currentStream = null;
let lastTranslation = '';
let originalTextAccumulator = '';
let translationTextAccumulator = '';
let processorNode = null;
let isConnected = false;
let sourceNode = null;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function updateSelectedLanguages() {
    const source = sourceLanguage.options[sourceLanguage.selectedIndex].text;
    const target = targetLanguage.options[targetLanguage.selectedIndex].text;
    selectedLanguages.innerHTML = `<strong>üéôÔ∏è Input:</strong> ${source} ‚Üí <strong>üåê Translation:</strong> ${target}`;
}

function updateTranscription(data) {
    if (data.original) {
        if (data.is_final) {
            originalTextAccumulator += data.original + ' ';
            originalDisplay.textContent = originalTextAccumulator.trim();
        } else {
            originalDisplay.textContent = (originalTextAccumulator + data.original).trim();
        }
        originalDisplay.classList.add('active');
        setTimeout(() => originalDisplay.classList.remove('active'), 2000);
    }
    
    if (data.translation) {
        if (data.is_final) {
            translationTextAccumulator += data.translation + ' ';
            translationDisplay.textContent = translationTextAccumulator.trim();
            lastTranslation = translationTextAccumulator.trim();
            speakTranslationBtn.disabled = false;
        } else {
            translationDisplay.textContent = (translationTextAccumulator + data.translation).trim();
        }
        translationDisplay.classList.add('active');
        setTimeout(() => translationDisplay.classList.remove('active'), 2000);
    }
}

function setStatus(status, text) {
    statusDot.className = `dot ${status}`;
    statusText.textContent = text;
}

// ============================================================================
// AUDIO RECORDING
// ============================================================================

async function startRecording() {
    try {
        console.log('Requesting microphone access...');
        
        // Request microphone with specific constraints
        currentStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            } 
        });
        
        console.log('Microphone access granted, creating audio context...');
        
        // Create audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ 
            sampleRate: 16000,
            latencyHint: 'interactive'
        });
        
        // Create source from stream
        sourceNode = audioContext.createMediaStreamSource(currentStream);
        
        // Create script processor
        processorNode = audioContext.createScriptProcessor(4096, 1, 1);
        
        processorNode.onaudioprocess = (e) => {
            if (!isRecording) return;
            
            try {
                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = new Int16Array(inputData.length);
                
                // Convert float32 to int16
                for (let i = 0; i < inputData.length; i++) {
                    const s = Math.max(-1, Math.min(1, inputData[i]));
                    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                
                // Store for playback
                audioChunks.push(pcmData.buffer);
                
                // Send to server
                const uint8Array = new Uint8Array(pcmData.buffer);
                const base64Audio = btoa(String.fromCharCode.apply(null, uint8Array));
                socket.emit('audio_data', { audio: base64Audio });
            } catch (error) {
                console.error('Error processing audio:', error);
            }
        };
        
        // Connect nodes
        sourceNode.connect(processorNode);
        processorNode.connect(audioContext.destination);
        
        console.log('Audio recording started successfully');
        return true;
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        
        let errorMessage = 'Could not access microphone. ';
        if (error.name === 'NotAllowedError') {
            errorMessage += 'Please allow microphone access in your browser settings.';
        } else if (error.name === 'NotFoundError') {
            errorMessage += 'No microphone found on this device.';
        } else {
            errorMessage += error.message;
        }
        
        alert('üé§ ' + errorMessage);
        return false;
    }
}

function stopRecording() {
    console.log('Stopping recording...');
    isRecording = false;
    
    // Disconnect and cleanup audio nodes
    if (processorNode) {
        try {
            processorNode.disconnect();
            processorNode.onaudioprocess = null;
        } catch (e) {
            console.error('Error disconnecting processor:', e);
        }
        processorNode = null;
    }
    
    if (sourceNode) {
        try {
            sourceNode.disconnect();
        } catch (e) {
            console.error('Error disconnecting source:', e);
        }
        sourceNode = null;
    }
    
    if (audioContext) {
        audioContext.close()
            .then(() => console.log('AudioContext closed'))
            .catch(e => console.error('Error closing AudioContext:', e));
        audioContext = null;
    }
    
    if (currentStream) {
        currentStream.getTracks().forEach(track => {
            track.stop();
            console.log('Track stopped:', track.label);
        });
        currentStream = null;
    }
    
    console.log('Recording stopped successfully');
}

// ============================================================================
// SOCKET EVENT LISTENERS
// ============================================================================

socket.on('connect', () => {
    console.log('Socket connected');
    isConnected = true;
    setStatus('', 'Ready to Start');
    originalDisplay.textContent = 'Click "Start Recording" to begin...';
    startBtn.disabled = false;
});

socket.on('connected', (data) => {
    sessionId = data.session_id;
    console.log('Session ID received:', sessionId);
    isConnected = true;
    setStatus('', 'Connected - Ready to Start');
    originalDisplay.textContent = 'Click "Start Recording" to begin...';
    startBtn.disabled = false;
});

socket.on('session_started', () => {
    console.log('Session started event received');
    isRecording = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus('active', 'üéôÔ∏è Recording');
    
    originalTextAccumulator = '';
    translationTextAccumulator = '';
    audioChunks = [];
    lastTranslation = '';
    
    originalDisplay.textContent = 'üëÇ Listening... Speak now!';
    translationDisplay.textContent = 'Translation will appear here...';
    speakTranslationBtn.disabled = true;
});

socket.on('session_stopped', () => {
    console.log('Session stopped event received');
    isRecording = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    playbackBtn.disabled = audioChunks.length === 0;
    downloadAudioBtn.disabled = audioChunks.length === 0;
    downloadTextBtn.disabled = false;
    setStatus('', 'Session Stopped');
    stopRecording();
});

socket.on('transcription', (data) => {
    console.log('Transcription received:', data);
    updateTranscription(data);
});

socket.on('error', (data) => {
    console.error('Socket error:', data);
    alert(`‚ö†Ô∏è Error: ${data.message}`);
    setStatus('error', 'Error');
    stopRecording();
    isRecording = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
});

socket.on('disconnect', () => {
    console.log('Socket disconnected');
    isConnected = false;
    setStatus('error', 'Disconnected - Reconnecting...');
    originalDisplay.textContent = 'Disconnected from server. Attempting to reconnect...';
    stopRecording();
    isRecording = false;
    startBtn.disabled = true;
    stopBtn.disabled = true;
});

socket.on('reconnect', (attemptNumber) => {
    console.log('Reconnected after', attemptNumber, 'attempts');
    isConnected = true;
    setStatus('', 'Reconnected - Ready to Start');
    originalDisplay.textContent = 'Reconnected! Click "Start Recording" to begin...';
    startBtn.disabled = false;
});

// ============================================================================
// BUTTON EVENT LISTENERS
// ============================================================================

startBtn.addEventListener('click', async () => {
    console.log('Start button clicked');
    
    if (!isConnected) {
        alert('‚ö†Ô∏è Not connected to server. Please wait...');
        return;
    }
    
    // Disable button immediately to prevent double-click
    startBtn.disabled = true;
    setStatus('', 'Starting...');
    
    const canRecord = await startRecording();
    if (!canRecord) {
        console.error('Failed to start recording');
        startBtn.disabled = false;
        setStatus('', 'Ready to Start');
        return;
    }
    
    playbackBtn.disabled = true;
    downloadAudioBtn.disabled = true;
    downloadTextBtn.disabled = true;
    speakTranslationBtn.disabled = true;
    
    console.log('Emitting start_session event');
    socket.emit('start_session', {
        source_language: sourceLanguage.value,
        target_language: targetLanguage.value
    });
});

stopBtn.addEventListener('click', () => {
    console.log('Stop button clicked');
    socket.emit('stop_session');
});

playbackBtn.addEventListener('click', () => {
    if (audioChunks.length === 0) {
        alert('No audio recorded for playback.');
        return;
    }
    
    if (playbackAudio.src) {
        playbackAudio.pause();
        playbackAudio.src = '';
    }
    
    const combinedPcmData = new Int16Array(audioChunks.reduce((acc, chunk) => acc + chunk.byteLength, 0) / 2);
    let offset = 0;
    for (const chunk of audioChunks) {
        combinedPcmData.set(new Int16Array(chunk), offset);
        offset += chunk.byteLength / 2;
    }

    const sampleRate = 16000;
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = combinedPcmData.byteLength;
    const fileLength = dataSize + 36;

    const buffer = new ArrayBuffer(fileLength + 8);
    const view = new DataView(buffer);

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    writeString(view, 0, 'RIFF');
    view.setUint32(4, fileLength, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    for (let i = 0; i < combinedPcmData.length; i++) {
        view.setInt16(44 + i * 2, combinedPcmData[i], true);
    }

    const blob = new Blob([view], { type: 'audio/wav' });
    playbackAudio.src = URL.createObjectURL(blob);
    playbackAudio.play();
});

downloadAudioBtn.addEventListener('click', () => {
    if (!sessionId) {
        alert('No active session ID to download audio.');
        return;
    }
    window.open(`/api/download/${sessionId}/audio`, '_blank');
});

downloadTextBtn.addEventListener('click', () => {
    if (!sessionId) {
        alert('No active session ID to download text.');
        return;
    }
    window.open(`/api/download/${sessionId}/text`, '_blank');
});

speakTranslationBtn.addEventListener('click', () => {
    if (lastTranslation) {
        const utterance = new SpeechSynthesisUtterance(lastTranslation);
        utterance.lang = targetLanguage.value;
        speechSynthesis.speak(utterance);
    }
});

sourceLanguage.addEventListener('change', updateSelectedLanguages);
targetLanguage.addEventListener('change', updateSelectedLanguages);

// ============================================================================
// INITIALIZATION
// ============================================================================

updateSelectedLanguages();
setStatus('', 'Connecting...');
startBtn.disabled = true;
console.log('App initialized, waiting for socket connection...');

