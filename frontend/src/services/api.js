/**
 * Backend API Client for AwaazWeb
 * Powered by Sarvam AI for Speech-to-Text and Text-to-Speech
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function createSession() {
  const res = await fetch(`${API_BASE}/api/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  return res.json();
}

/**
 * Sends recorded microphone audio to Sarvam STT & backend orchestrator.
 */
export async function sendVoiceAudio(sessionId, audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'input.webm');
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  const res = await fetch(`${API_BASE}/api/voice`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Voice processing error (${res.status}): ${errText}`);
  }
  return res.json();
}

/**
 * Direct Speech-to-Text conversion using Sarvam AI Saaras model.
 */
export async function convertSpeechToText(audioBlob, languageCode = 'hi-IN') {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'audio.webm');
  formData.append('language_code', languageCode);

  const res = await fetch(`${API_BASE}/api/stt`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Sarvam STT failed (${res.status}): ${errText}`);
  }
  return res.json();
}

/**
 * Direct Text-to-Speech synthesis using Sarvam AI Bulbul model.
 * Returns audio Blob (audio/wav).
 */
export async function convertTextToSpeech(text, { languageCode = 'hi-IN', speaker = 'shubh', pace = 1.0 } = {}) {
  const res = await fetch(`${API_BASE}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      language_code: languageCode,
      speaker,
      pace,
      format: 'audio',
    }),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Sarvam TTS failed (${res.status}): ${errText}`);
  }
  return res.blob();
}

export async function sendTextInput(sessionId, text) {
  const res = await fetch(`${API_BASE}/api/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Text query failed (${res.status}): ${errText}`);
  }
  return res.json();
}

export async function sendConfirmation(sessionId, approved) {
  const res = await fetch(`${API_BASE}/api/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, approved }),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Confirmation failed (${res.status}): ${errText}`);
  }
  return res.json();
}

export async function undoLastAction(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/undo`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Undo failed: ${res.statusText}`);
  return res.json();
}

export async function getSessionLog(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/log`);
  if (!res.ok) throw new Error(`Failed to fetch logs: ${res.statusText}`);
  return res.json();
}

export async function getBrowserState(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/browser-state`);
  if (!res.ok) throw new Error(`Failed to fetch browser state: ${res.statusText}`);
  return res.json();
}

export async function stopSessionTask(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Stop task failed: ${res.statusText}`);
  return res.json();
}

export async function getSessionScreenshot(sessionId, url = null, refresh = false) {
  const params = new URLSearchParams();
  if (url) params.set('url', url);
  if (refresh) params.set('refresh', 'true');
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/screenshot${queryStr}`);
  if (!res.ok) throw new Error(`Failed to fetch screenshot: ${res.statusText}`);
  return res.json();
}

export async function sendBrowserAction(sessionId, action, target = null) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, target }),
  });
  if (!res.ok) throw new Error(`Browser action failed: ${res.statusText}`);
  return res.json();
}

export function subscribeSessionStream(sessionId, onEvent, onError) {
  if (!sessionId) return () => {};
  const eventSource = new EventSource(`${API_BASE}/api/session/${sessionId}/stream`);

  eventSource.addEventListener('hydrate', (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent('hydrate', data);
    } catch (err) {
      console.warn('SSE hydrate parse error', err);
    }
  });

  eventSource.addEventListener('browser_stream', (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent('browser_stream', data);
    } catch (err) {
      console.warn('SSE browser_stream parse error', err);
    }
  });

  eventSource.addEventListener('step', (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent('step', data);
    } catch (err) {
      console.warn('SSE step parse error', err);
    }
  });

  eventSource.addEventListener('status', (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent('status', data);
    } catch (err) {
      console.warn('SSE status parse error', err);
    }
  });

  eventSource.onerror = (err) => {
    if (onError) onError(err);
  };

  return () => {
    eventSource.close();
  };
}
