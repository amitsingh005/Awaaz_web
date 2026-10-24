import React from 'react';

/**
 * High-contrast, accessible large button for blind users.
 * Supports touch, click, and Spacebar trigger.
 */
export default function TalkButton({ isRecording, onToggleRecord, disabled }) {
  return (
    <button
      id="talk-button"
      className={`talk-button ${isRecording ? 'recording' : ''}`}
      onClick={onToggleRecord}
      disabled={disabled}
      aria-label={isRecording ? 'Listening. Click to stop speaking.' : 'Click to talk or press Space bar'}
      aria-pressed={isRecording}
    >
      <div className="mic-icon-wrapper">
        <svg viewBox="0 0 24 24" fill="currentColor" className="mic-icon" width="48" height="48">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
        </svg>
      </div>
      <span className="talk-label">
        {isRecording ? 'Bolte Rahiye (Sun Raha Hoon...)' : 'Bolne Ke Liye Dabayein (Space Bar)'}
      </span>
    </button>
  );
}
