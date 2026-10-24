import React from 'react';

/**
 * Always-visible high-contrast status banner announcing the current assistant state.
 */
export default function StatusBanner({ state, message }) {
  const stateLabels = {
    idle: 'Taiyaar (Ready)',
    working: 'Kaam Ho Raha Hai (Working...)',
    needs_confirmation: 'Pushti Chahiye (Confirmation Needed)',
    needs_user_input: 'Aapki Madad Chahiye (Input Needed)',
    done: 'Ho Gaya (Done)',
    error: 'Rukawat (Error)',
  };

  return (
    <div
      id="status-banner"
      className={`status-banner status-${state || 'idle'}`}
      role="status"
      aria-live="polite"
    >
      <div className="status-indicator"></div>
      <div className="status-info">
        <span className="status-state">{stateLabels[state] || state}</span>
        {message && <span className="status-detail">{message}</span>}
      </div>
    </div>
  );
}
