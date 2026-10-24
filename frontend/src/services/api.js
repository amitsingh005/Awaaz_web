/**
 * Backend API Client for AwaazWeb
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function createSession() {
  const res = await fetch(`${API_BASE}/api/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return res.json();
}

export async function sendVoiceAudio(sessionId, audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'input.webm');
  formData.append('session_id', sessionId);

  const res = await fetch(`${API_BASE}/api/voice`, {
    method: 'POST',
    body: formData,
  });
  return res.json();
}

export async function sendTextInput(sessionId, text) {
  const res = await fetch(`${API_BASE}/api/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  return res.json();
}

export async function sendConfirmation(sessionId, approved) {
  const res = await fetch(`${API_BASE}/api/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, approved }),
  });
  return res.json();
}

export async function undoLastAction(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/undo`, {
    method: 'POST',
  });
  return res.json();
}

export async function getSessionLog(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/log`);
  return res.json();
}
