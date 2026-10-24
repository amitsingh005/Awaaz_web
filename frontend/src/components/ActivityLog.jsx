import React from 'react';

/**
 * Activity log showing real-time agent thoughts, search steps, and actions
 * so sighted judges and developers can observe backend navigation live.
 */
export default function ActivityLog({ logs = [] }) {
  return (
    <section className="activity-log-section" aria-label="Activity Log">
      <h2 className="log-title">Live Activity Log</h2>
      <div className="log-container" role="log">
        {logs.length === 0 ? (
          <p className="log-empty">Waiting for user voice command...</p>
        ) : (
          <ul className="log-list">
            {logs.map((item, idx) => (
              <li key={idx} className={`log-item log-${item.type || 'info'}`}>
                <span className="log-timestamp">{item.time || ''}</span>
                <span className="log-message">{item.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
