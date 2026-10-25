import React from 'react';

/**
 * AgentTimeline Component
 * Right panel displaying real-time agent activity, chronological action timeline,
 * verification statuses, stop controls, and final results.
 */
export default function AgentTimeline({
  originalCommand,
  currentStatus,
  currentAction,
  steps = [],
  finalResult,
  verificationStatus,
  onStop,
  isStopping = false,
}) {
  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const failedCount = steps.filter((s) => s.status === 'failed').length;
  const isTaskActive = currentStatus === 'working' || currentStatus === 'executing' || currentStatus === 'needs_confirmation';

  // Helper for step icon based on action type
  const getStepIcon = (action) => {
    switch (action) {
      case 'plan':
        return '🧠';
      case 'search':
        return '🔍';
      case 'navigate':
        return '🌐';
      case 'safety_gate':
        return '🛡️';
      case 'credentials_handoff':
        return '🔑';
      case 'browser_step':
        return '⚡';
      case 'confirmation':
        return '✓';
      case 'cancellation':
      case 'stop':
        return '🛑';
      default:
        return '📌';
    }
  };

  // Helper for status badge
  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <span className="timeline-badge badge-success">Done</span>;
      case 'running':
      case 'in_progress':
        return <span className="timeline-badge badge-running">Running...</span>;
      case 'pending':
        return <span className="timeline-badge badge-pending">Pending</span>;
      case 'failed':
        return <span className="timeline-badge badge-failed">Failed</span>;
      default:
        return <span className="timeline-badge badge-info">{status || 'Info'}</span>;
    }
  };

  // Helper for verification badge
  const getVerificationBadge = (verif) => {
    switch (verif) {
      case 'verified':
      case 'verified_by_user':
      case 'verified_by_provider':
        return <span className="verif-tag verif-ok">✓ Verified</span>;
      case 'held_by_safety':
        return <span className="verif-tag verif-held">⚠️ Safety Gate Held</span>;
      case 'held_for_credentials':
        return <span className="verif-tag verif-held">🔒 Credentials Required</span>;
      case 'cancelled_by_user':
        return <span className="verif-tag verif-cancel">Cancelled</span>;
      case 'limit_reached':
        return <span className="verif-tag verif-limit">Cap Reached</span>;
      default:
        return null;
    }
  };

  return (
    <section className="agent-activity-panel" aria-label="Agent Activity and Execution Timeline">
      {/* Panel Header */}
      <div className="activity-panel-header">
        <div>
          <h2 className="activity-title">Agent Activity</h2>
          <p className="activity-subtitle">Real-time browser operation & safety timeline</p>
        </div>

        {/* Real Stop / Halt Control */}
        <div className="activity-actions">
          <button
            type="button"
            className="stop-action-btn"
            onClick={onStop}
            disabled={!isTaskActive || isStopping}
            title={isTaskActive ? 'Halt current task immediately' : 'No active task running'}
            aria-label={isTaskActive ? 'Stop current task' : 'No active task to stop'}
          >
            {isStopping ? 'Stopping...' : isTaskActive ? '⏹ Stop Task' : '✓ Agent Idle'}
          </button>
        </div>
      </div>

      {/* Overview Cards: Command & Current Task Status */}
      <div className="activity-summary-grid">
        <div className="summary-card">
          <span className="summary-label">Original Command</span>
          <p className="summary-value command-value">
            {originalCommand ? `"${originalCommand}"` : <em>No active command yet</em>}
          </p>
        </div>

        <div className="summary-card">
          <span className="summary-label">Task Status</span>
          <div className="status-row">
            <span className={`status-indicator-dot dot-${currentStatus || 'idle'}`} />
            <strong className="status-name">
              {currentStatus === 'working' || currentStatus === 'executing'
                ? 'Executing...'
                : currentStatus === 'needs_confirmation'
                ? 'Awaiting Confirmation'
                : currentStatus === 'needs_user_input'
                ? 'Awaiting Screen OTP'
                : currentStatus === 'completed' || currentStatus === 'done'
                ? 'Completed'
                : currentStatus === 'cancelled'
                ? 'Cancelled'
                : 'Idle'}
            </strong>
          </div>
          {currentAction && (
            <p className="current-action-text" title={currentAction}>
              ↳ {currentAction}
            </p>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="activity-metrics-row">
        <div className="metric-chip">
          <span className="metric-num">{steps.length}</span>
          <span className="metric-label">Total Steps</span>
        </div>
        <div className="metric-chip">
          <span className="metric-num text-emerald">{completedCount}</span>
          <span className="metric-label">Completed</span>
        </div>
        <div className="metric-chip">
          <span className="metric-num text-rose">{failedCount}</span>
          <span className="metric-label">Failed</span>
        </div>
        <div className="metric-chip">
          <span className="metric-label">Verification:</span>
          <span className="metric-verif">
            {verificationStatus === 'verified' ? '✓ Verified' : verificationStatus || 'Active'}
          </span>
        </div>
      </div>

      {/* Chronological Action Timeline */}
      <div className="timeline-container" role="region" aria-label="Action Timeline">
        <h3 className="timeline-heading">Action Timeline ({steps.length})</h3>

        {steps.length === 0 ? (
          <div className="timeline-empty">
            <span className="empty-icon">⏳</span>
            <p>Waiting for commands. Steps executed by the browser agent will appear chronologically here.</p>
          </div>
        ) : (
          <ol className="timeline-list">
            {steps.map((step, idx) => {
              const isCurrent = idx === steps.length - 1 && (step.status === 'running' || step.status === 'pending');
              return (
                <li
                  key={step.id || `step-${idx}`}
                  className={`timeline-entry ${isCurrent ? 'entry-active' : ''} entry-${step.status || 'info'}`}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  <div className="timeline-node" aria-hidden="true">
                    <span className="node-icon">{getStepIcon(step.action)}</span>
                  </div>

                  <div className="timeline-body">
                    <div className="entry-header">
                      <span className="entry-id">#{step.id || `S${idx + 1}`}</span>
                      <time className="entry-time">
                        {step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : ''}
                      </time>
                      <div className="entry-badges">
                        {getStatusBadge(step.status)}
                        {getVerificationBadge(step.verification_status)}
                      </div>
                    </div>

                    <p className="entry-description">{step.description}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      {/* Final Result Card */}
      {finalResult && (
        <div className="final-result-card" role="region" aria-label="Final Execution Result">
          <div className="final-result-header">
            <span className="result-icon">✨</span>
            <span className="result-title">Final Result</span>
          </div>
          <p className="result-text">{finalResult}</p>
        </div>
      )}
    </section>
  );
}
