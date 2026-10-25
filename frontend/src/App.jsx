import React, { useState, useEffect, useCallback, useRef } from 'react';
import TalkButton from './components/TalkButton';
import StatusBanner from './components/StatusBanner';
import ActivityLog from './components/ActivityLog';
import BrowserPreview from './components/BrowserPreview';
import AgentTimeline from './components/AgentTimeline';
import { useRecorder } from './hooks/useRecorder';
import { useSpeaker } from './hooks/useSpeaker';
import { playSound } from './services/soundEffects';
import {
  createSession,
  sendVoiceAudio,
  sendTextInput,
  sendConfirmation,
  getSessionLog,
  getBrowserState,
  stopSessionTask,
  subscribeSessionStream,
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
  const [_pendingAction, setPendingAction] = useState(null);

  // Agentic Browser state
  const [currentUrl, setCurrentUrl] = useState('');
  const [streamingUrl, setStreamingUrl] = useState('');
  const [screenshotUrl, setScreenshotUrl] = useState('');
  const [pageTitle, setPageTitle] = useState('');
  const [steps, setSteps] = useState([]);
  const [currentAction, setCurrentAction] = useState('');
  const [finalResult, setFinalResult] = useState('');
  const [verificationStatus, setVerificationStatus] = useState('unverified');
  const [isStopping, setIsStopping] = useState(false);

  const { isRecording, permissionStatus, startRecording, stopRecording } = useRecorder();
  const { speak, stop: stopSpeaking, isSpeaking, isLoadingTTS, engineName } = useSpeaker();
  const isProcessingRef = useRef(false);

  const addLog = useCallback((message, type = 'info') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogs((prev) => [...prev, { time, message, type }]);
  }, []);

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
  }, [addLog]);

  // Subscribe to real-time browser stream & timeline events
  useEffect(() => {
    if (!sessionId) return;

    // 1. Initial hydration via REST
    getBrowserState(sessionId)
      .then((data) => {
        if (data) {
          if (data.current_url) setCurrentUrl(data.current_url);
          if (data.streaming_url) setStreamingUrl(data.streaming_url);
          if (data.steps && data.steps.length > 0) setSteps(data.steps);
          if (data.current_action) setCurrentAction(data.current_action);
          if (data.final_result) setFinalResult(data.final_result);
          if (data.verification_status) setVerificationStatus(data.verification_status);
        }
      })
      .catch((err) => {
        console.warn('Could not hydrate browser state:', err);
      });

    // 2. Real-time Server-Sent Events stream
    const unsubscribe = subscribeSessionStream(
      sessionId,
      (eventType, data) => {
        if (eventType === 'hydrate') {
          if (data.current_url) setCurrentUrl(data.current_url);
          if (data.streaming_url) setStreamingUrl(data.streaming_url);
          if (data.steps) setSteps(data.steps);
          if (data.current_action) setCurrentAction(data.current_action);
          if (data.final_result) setFinalResult(data.final_result);
          if (data.verification_status) setVerificationStatus(data.verification_status);
        } else if (eventType === 'browser_stream') {
          if (data.url) setCurrentUrl(data.url);
          if (data.streaming_url) setStreamingUrl(data.streaming_url);
          if (data.screenshot_url !== undefined) setScreenshotUrl(data.screenshot_url);
          if (data.title) setPageTitle(data.title);
          if (data.verification_status) setVerificationStatus(data.verification_status);
          addLog(`Browser navigated to: ${data.url || data.streaming_url || 'new page'}`, 'info');
        } else if (eventType === 'step') {
          setSteps((prev) => {
            const stepId = data.id;
            const existsIndex = stepId ? prev.findIndex((s) => s.id === stepId) : -1;
            if (existsIndex >= 0) {
              const updated = [...prev];
              updated[existsIndex] = { ...updated[existsIndex], ...data };
              return updated;
            }
            return [...prev, data];
          });
          if (data.description) {
            addLog(`Agent: ${data.description}`, data.status === 'failed' ? 'error' : 'info');
          }
        } else if (eventType === 'status') {
          if (data.current_action) setCurrentAction(data.current_action);
          if (data.final_result) setFinalResult(data.final_result);
          if (data.verification_status) setVerificationStatus(data.verification_status);
          if (data.status) {
            if (data.status === 'completed') {
              setState('done');
            } else if (data.status === 'cancelled') {
              setState('idle');
              setIsStopping(false);
            }
          }
        }
      },
      (err) => {
        console.warn('SSE connection warning:', err);
      }
    );

    return () => {
      unsubscribe();
    };
  }, [sessionId, addLog]);

  // Sync server logs
  const refreshLogs = useCallback(async (sid) => {
    if (!sid) return;
    try {
      const res = await getSessionLog(sid);
      if (res && res.logs && res.logs.length > 0) {
        setLogs(res.logs);
      }
    } catch {
      // ignore background refresh failure
    }
  }, []);

  // Process assistant reply with Sarvam AI audio playback
  const handleAssistantReply = useCallback(
    (reply) => {
      if (reply.session_id) {
        setSessionId(reply.session_id);
      }
      setState(reply.state || 'done');
      setTranscript(reply.transcript || '');
      setReplyText(reply.reply_text || '');
      setOptions(reply.options || []);
      setPendingAction(reply.pending_action || null);
      if (reply.reply_text) {
        setFinalResult(reply.reply_text);
      }

      if (reply.narration && reply.narration.length > 0) {
        reply.narration.forEach((narr) => addLog(narr, 'info'));
      }

      if (reply.state === 'error') {
        playSound('error');
        setStatusMessage('Rukawat aayi hai.');
      } else if (reply.state === 'needs_confirmation') {
        playSound('error');
        setStatusMessage('Pushti Chahiye: Kripya "Haan" ya "Nahi" bolein.');
      } else {
        playSound('done');
        setStatusMessage('Jawaab taiyaar hai.');
      }

      // Play audio response using Sarvam AI Bulbul TTS
      if (reply.reply_text) {
        addLog('Playing Sarvam AI Bulbul voice response...', 'info');
        speak({
          text: reply.reply_text,
          audioBase64: reply.audio_base64,
        });
      }
    },
    [addLog, speak]
  );

  // Handle Voice Toggle (Mic Record -> Sarvam STT -> Intent -> Sarvam TTS)
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
        const errMsg = err.message || 'Microphone access denied.';
        setStatusMessage(errMsg);
        addLog('Microphone error: ' + errMsg, 'error');
      }
    } else {
      try {
        isProcessingRef.current = true;
        playSound('working');
        setStatusMessage('Sarvam AI Saaras aawaz samajh raha hai...');
        addLog('Transcribing voice via Sarvam AI Saaras (Hindi/Hinglish)...', 'info');

        const blob = await stopRecording();
        if (!blob || blob.size === 0) {
          isProcessingRef.current = false;
          setState('idle');
          setStatusMessage('Koi aawaz nahi mili.');
          return;
        }

        let activeSessionId = sessionId;
        if (!activeSessionId) {
          try {
            const sRes = await createSession();
            if (sRes && sRes.session_id) {
              activeSessionId = sRes.session_id;
              setSessionId(sRes.session_id);
            }
          } catch {
            // Backend will auto-create session if not provided
          }
        }

        const reply = await sendVoiceAudio(activeSessionId, blob);
        if (reply.session_id) {
          setSessionId(reply.session_id);
        }
        handleAssistantReply(reply);
        refreshLogs(reply.session_id || activeSessionId);
      } catch (err) {
        playSound('error');
        setState('error');
        setStatusMessage('Sarvam AI process error: ' + (err.message || 'Server error'));
        addLog('Voice pipeline error: ' + err.message, 'error');
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

  // Handle explicit confirmation button clicks
  const handleConfirmAction = async (approved) => {
    if (isProcessingRef.current) return;
    try {
      isProcessingRef.current = true;
      stopSpeaking();
      playSound('working');
      setState('working');
      setStatusMessage(approved ? 'Kadam confirm ho raha hai...' : 'Kadam cancel ho raha hai...');
      addLog(`User clicked ${approved ? 'YES (Confirm)' : 'NO (Cancel)'}`, 'warning');

      const reply = await sendConfirmation(sessionId, approved);
      handleAssistantReply(reply);
      refreshLogs(sessionId);
    } catch (err) {
      playSound('error');
      setState('error');
      setStatusMessage('Confirmation failed.');
      addLog('Confirmation error: ' + err.message, 'error');
    } finally {
      isProcessingRef.current = false;
    }
  };

  // Real task cancellation / Stop control
  const handleStopTask = async () => {
    if (!sessionId || isStopping) return;
    try {
      setIsStopping(true);
      stopSpeaking();
      playSound('error');
      addLog('User requested task stop / cancellation', 'warning');
      await stopSessionTask(sessionId);
      setState('idle');
      setStatusMessage('Process rok diya gaya.');
    } catch (err) {
      console.error('Stop error:', err);
      addLog('Stop error: ' + err.message, 'error');
    } finally {
      setIsStopping(false);
    }
  };

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

      let activeSessionId = sessionId;
      if (!activeSessionId) {
        try {
          const sRes = await createSession();
          if (sRes && sRes.session_id) {
            activeSessionId = sRes.session_id;
            setSessionId(sRes.session_id);
          }
        } catch {
          // Backend will auto-create session
        }
      }

      const reply = await sendTextInput(activeSessionId, query);
      if (reply.session_id) {
        setSessionId(reply.session_id);
      }
      handleAssistantReply(reply);
      refreshLogs(reply.session_id || activeSessionId);
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
          <span className="voice-icon">{isSpeaking ? '🔊' : isLoadingTTS ? '⏳' : '✨'}</span>
          <span>
            Voice AI: {engineName || 'Sarvam AI Bulbul & Saaras'} (Hindi & Hinglish)
            {isSpeaking ? ' · Bol raha hai...' : ''}
            {isLoadingTTS ? ' · Voice taiyaar ho rahi hai...' : ''}
          </span>
        </div>
      </header>

      {/* Permission alert banner if microphone access is blocked */}
      {permissionStatus === 'denied' && (
        <section
          className="confirm-gate-box"
          style={{ borderColor: '#ef4444', backgroundColor: '#450a0a' }}
          aria-label="Microphone Permission Required"
        >
          <p className="confirm-gate-title">🎙️ Microphone Permission Denied</p>
          <p style={{ color: '#fca5a5', marginTop: '0.25rem', fontSize: '0.95rem' }}>
            Browser ne microphone access block kiya hua hai. AwaazWeb se baat karne ke liye, kripya browser address bar mein lock icon par click karein aur Microphone permission "Allow" karein, fir page refresh karein.
          </p>
        </section>
      )}

      {/* Split-Screen Agentic Interface */}
      <div className="agent-split-screen">
        {/* LEFT PANEL — Live Browser Viewport */}
        <div className="split-panel-left">
          <BrowserPreview
            sessionId={sessionId}
            currentUrl={currentUrl}
            streamingUrl={streamingUrl}
            screenshotUrl={screenshotUrl}
            verificationStatus={verificationStatus}
            isLoading={state === 'working'}
            status={state}
            title={pageTitle}
          />
        </div>

        {/* RIGHT PANEL — Controls & Agent Activity */}
        <div className="split-panel-right">
          {/* High-contrast status banner */}
          <StatusBanner state={state} message={statusMessage} />

          {/* Safety Gate Explicit Confirmation Prompt */}
          {state === 'needs_confirmation' && (
            <section className="confirm-gate-box" aria-label="Confirmation Required">
              <p className="confirm-gate-title">⚠️ Mahatvapurna Kadam: Kya aap aage badhna chahte hain?</p>
              <div className="confirm-actions-wrapper" role="group" aria-label="Pushti Vikalp">
                <button
                  type="button"
                  className="confirm-btn confirm-yes"
                  onClick={() => handleConfirmAction(true)}
                  aria-label="Haan, Kadam pura karo"
                >
                  ✓ Haan (Confirm)
                </button>
                <button
                  type="button"
                  className="confirm-btn confirm-no"
                  onClick={() => handleConfirmAction(false)}
                  aria-label="Nahi, Cancel karo"
                >
                  ✕ Nahi (Cancel)
                </button>
              </div>
            </section>
          )}

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

          {/* Live Agent Activity & Timeline Panel */}
          <AgentTimeline
            originalCommand={transcript || (steps.length > 0 ? steps[0]?.description : '')}
            currentStatus={state}
            currentAction={currentAction}
            steps={steps}
            finalResult={finalResult || replyText}
            verificationStatus={verificationStatus}
            onStop={handleStopTask}
            isStopping={isStopping}
          />

          {/* Visual Activity Log for sighted judges & developers */}
          <ActivityLog logs={logs} />
        </div>
      </div>
    </main>
  );
}
