import React, { useState, useEffect, useCallback, useRef } from 'react';
import TalkButton from './components/TalkButton';
import StatusBanner from './components/StatusBanner';
import ActivityLog from './components/ActivityLog';
import { useRecorder } from './hooks/useRecorder';
import { useSpeaker } from './hooks/useSpeaker';
import { playSound } from './services/soundEffects';
import {
  createSession,
  sendVoiceAudio,
  sendTextInput,
  getSessionLog,
} from './services/api';

export default function App() {
  const [sessionId, setSessionId] = useState('');
  const [state, setState] = useState('idle'); // idle | working | needs_confirmation | needs_user_input | done | error
  const [statusMessage, setStatusMessage] = useState('Aapki baat sunne ke liye taiyaar.');
  const [transcript, setTranscript] = useState('');
  const [replyText, setReplyText] = useState('');
  const [options, setOptions] = useState([]);
  const [logs, setLogs] = useState([]);
  const [typedInput, setTypedInput] = useState('');

  const { isRecording, startRecording, stopRecording } = useRecorder();
  const { speak, stop: stopSpeaking, hindiVoice, isSpeaking } = useSpeaker();
  const isProcessingRef = useRef(false);

  // Initialize session on load
  useEffect(() => {
    async function initSession() {
      try {
        const res = await createSession();
        if (res && res.session_id) {
          setSessionId(res.session_id);
          addLog('Session initialized: ' + res.session_id.slice(0, 8) + '...', 'info');
        }
      } catch (err) {
        console.error('Failed to create session:', err);
        addLog('Backend offline or unreachable', 'error');
      }
    }
    initSession();
  }, []);

  const addLog = useCallback((message, type = 'info') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogs((prev) => [...prev, { time, message, type }]);
  }, []);

  // Sync server logs
  const refreshLogs = useCallback(async (sid) => {
    if (!sid) return;
    try {
      const res = await getSessionLog(sid);
      if (res && res.logs && res.logs.length > 0) {
        setLogs(res.logs);
      }
    } catch (e) {
      // ignore background refresh failure
    }
  }, []);

  // Process assistant reply
  const handleAssistantReply = useCallback(
    (reply) => {
      setState(reply.state || 'done');
      setTranscript(reply.transcript || '');
      setReplyText(reply.reply_text || '');
      setOptions(reply.options || []);

      if (reply.narration && reply.narration.length > 0) {
        reply.narration.forEach((narr) => addLog(narr, 'info'));
      }

      if (reply.state === 'error') {
        playSound('error');
        setStatusMessage('Rukawat aayi hai.');
      } else {
        playSound('done');
        setStatusMessage('Jawaab taiyaar hai.');
      }

      // Speak reply text using SpeechSynthesis (preferably hi-IN)
      if (reply.reply_text) {
        speak(reply.reply_text);
      }
    },
    [addLog, speak]
  );

  // Handle Voice Toggle
  const handleToggleRecord = useCallback(async () => {
    if (isProcessingRef.current) return;

    if (!isRecording) {
      try {
        stopSpeaking();
        playSound('listening');
        setState('working');
        setStatusMessage('Sun raha hoon... Bolte rahiye.');
        addLog('Microphone active: recording speech...', 'info');
        await startRecording();
      } catch (err) {
        playSound('error');
        setState('error');
        setStatusMessage('Microphone access denied.');
        addLog('Microphone error: ' + err.message, 'error');
      }
    } else {
      try {
        isProcessingRef.current = true;
        playSound('working');
        setStatusMessage('Groq Whisper aawaz samajh raha hai...');
        addLog('Transcribing voice via Groq Whisper...', 'info');

        const blob = await stopRecording();
        if (!blob || blob.size === 0) {
          isProcessingRef.current = false;
          setState('idle');
          setStatusMessage('Koi aawaz nahi mili.');
          return;
        }

        const reply = await sendVoiceAudio(sessionId, blob);
        handleAssistantReply(reply);
        refreshLogs(sessionId);
      } catch (err) {
        playSound('error');
        setState('error');
        setStatusMessage('Server connection error.');
        addLog('Voice upload failed: ' + err.message, 'error');
      } finally {
        isProcessingRef.current = false;
      }
    }
  }, [
    isRecording,
    sessionId,
    startRecording,
    stopRecording,
    stopSpeaking,
    handleAssistantReply,
    refreshLogs,
    addLog,
  ]);

  // Spacebar to talk
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && !isRecording && !isProcessingRef.current) {
        e.preventDefault();
        handleToggleRecord();
      }
    };

    const handleKeyUp = (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && isRecording) {
        e.preventDefault();
        handleToggleRecord();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleToggleRecord, isRecording]);

  // Handle typed input (for testing without microphone)
  const handleSendText = async (e) => {
    e.preventDefault();
    const query = typedInput.trim();
    if (!query || isProcessingRef.current) return;

    try {
      isProcessingRef.current = true;
      stopSpeaking();
      playSound('working');
      setState('working');
      setStatusMessage('Processing typed query...');
      addLog(`Text query sent: "${query}"`, 'user');
      setTypedInput('');

      const reply = await sendTextInput(sessionId, query);
      handleAssistantReply(reply);
      refreshLogs(sessionId);
    } catch (err) {
      playSound('error');
      setState('error');
      setStatusMessage('Request error.');
      addLog('Text request failed: ' + err.message, 'error');
    } finally {
      isProcessingRef.current = false;
    }
  };

  const handleOptionClick = (optText) => {
    setTypedInput(optText);
  };

  return (
    <main className="app-container" role="main">
      <header className="app-header">
        <h1>AwaazWeb</h1>
        <p className="tagline">Hindi & Hinglish Autonomous Voice Web Navigator</p>
        <div className="voice-badge" aria-label="Speech output voice status">
          <span className="voice-icon">🎤</span>
          <span>
            Speech Engine:{' '}
            {hindiVoice ? `Hindi (${hindiVoice.lang} - ${hindiVoice.name})` : 'Default System Voice (Active)'}
          </span>
        </div>
      </header>

      {/* High-contrast status banner */}
      <StatusBanner state={state} message={statusMessage} />

      {/* Main Accessible Talk Button */}
      <div className="talk-button-wrapper">
        <TalkButton
          isRecording={isRecording}
          onToggleRecord={handleToggleRecord}
          disabled={state === 'working' && !isRecording}
        />
        <p className="talk-hint">
          Press <kbd>Space</kbd> key or tap the button to talk
        </p>
      </div>

      {/* Spoken Response & Transcript Display */}
      {(transcript || replyText) && (
        <section className="response-card" aria-live="polite" aria-label="Assistant Response">
          {transcript && (
            <div className="transcript-box">
              <span className="transcript-label">Aapne Kaha (Transcribed):</span>
              <p className="transcript-text">"{transcript}"</p>
            </div>
          )}
          {replyText && (
            <div className="reply-box">
              <span className="reply-label">AwaazWeb (Voice Reply):</span>
              <p className="reply-text">{replyText}</p>
            </div>
          )}

          {options.length > 0 && (
            <div className="options-wrapper">
              <span className="transcript-label">Suggested Options:</span>
              <div className="options-container" role="group" aria-label="Suggested follow-up options">
                {options.map((opt, i) => (
                  <button
                    key={i}
                    type="button"
                    className="option-pill"
                    onClick={() => handleOptionClick(opt)}
                    aria-label={`Option ${i + 1}: ${opt}`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Typed input fallback for non-mic testing */}
      <form className="text-fallback-form" onSubmit={handleSendText} aria-label="Typed query fallback">
        <input
          type="text"
          className="text-input"
          placeholder="Type in Hindi or Hinglish (e.g., Delhi se Bhopal train dhundho)..."
          value={typedInput}
          onChange={(e) => setTypedInput(e.target.value)}
          aria-label="Text input to test without microphone"
        />
        <button
          type="submit"
          className="send-button"
          disabled={!typedInput.trim() || state === 'working'}
        >
          Bhejo
        </button>
      </form>

      {/* Visual Activity Log for sighted judges & developers */}
      <ActivityLog logs={logs} />
    </main>
  );
}
