import React, { useState, useEffect, useRef } from 'react';
import { getSessionScreenshot, sendBrowserAction } from '../services/api';

/**
 * BrowserPreview Component
 * Left panel displaying verified Playwright screenshots of actual rendered websites.
 *
 * Design:
 *  - Screenshot-first (primary viewport renders the latest captured webpage snapshot)
 *  - Eliminates reliance on iframe embedding (which is blocked by X-Frame-Options/CSP)
 *  - Supports browser actions (scroll down, scroll up, refresh) with immediate snapshot update
 *  - Clearly shows loading, access-denied (WAF/403), auth-required, and error states
 *  - Transparently indicates read-only agent snapshot (non-interactive display)
 */
export default function BrowserPreview({
  sessionId,
  currentUrl,
  streamingUrl,
  screenshotUrl: propScreenshotUrl,
  verificationStatus: propVerificationStatus,
  isLoading,
  status,
  title,
}) {
  const [latestScreenshotUrl, setLatestScreenshotUrl] = useState('');
  const [screenshotAge, setScreenshotAge] = useState(null);
  const [localVerification, setLocalVerification] = useState('unverified');
  const [localMessage, setLocalMessage] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [actionFeedback, setActionFeedback] = useState('');

  const pollTimerRef = useRef(null);

  // Synchronize screenshot from props or SSE
  useEffect(() => {
    if (propScreenshotUrl) {
      setLatestScreenshotUrl(propScreenshotUrl);
      setScreenshotAge(new Date());
    }
  }, [propScreenshotUrl]);

  // Determine effective verification status
  const effectiveVerification =
    localVerification !== 'unverified'
      ? localVerification
      : propVerificationStatus || 'unverified';

  // Reset state when target URL changes
  useEffect(() => {
    setLatestScreenshotUrl('');
    setScreenshotAge(null);
    setLocalVerification('unverified');
    setLocalMessage('');
    setActionFeedback('');
    clearTimeout(pollTimerRef.current);
  }, [currentUrl, streamingUrl]);

  // Synchronize prop updates (only if local status is not already definitively access_denied / auth_required)
  useEffect(() => {
    if (
      propVerificationStatus &&
      propVerificationStatus !== 'unverified' &&
      !['access_denied', 'auth_required'].includes(localVerification)
    ) {
      setLocalVerification(propVerificationStatus);
    }
  }, [propVerificationStatus, localVerification]);

  // Fetch verified screenshot for current URL
  useEffect(() => {
    if (!sessionId || !currentUrl) return;

    let alive = true;
    clearTimeout(pollTimerRef.current);

    const fetchSnapshot = async (forceRefresh = false) => {
      try {
        setIsCapturing(true);
        const data = await getSessionScreenshot(sessionId, currentUrl, forceRefresh);
        if (!alive) return;

        if (data?.verification_status) {
          setLocalVerification(data.verification_status);
        }
        if (data?.message) {
          setLocalMessage(data.message);
        }

        if (data?.screenshot_url) {
          setLatestScreenshotUrl(data.screenshot_url);
          setScreenshotAge(new Date());
        }

        // Stop polling if access is denied, auth is required, or navigation failed
        if (['access_denied', 'auth_required', 'failed'].includes(data?.verification_status)) {
          setIsCapturing(false);
          return;
        }

        // Only schedule a poll if the agent is actively executing a task
        if (status === 'working') {
          pollTimerRef.current = setTimeout(() => fetchSnapshot(false), 5000);
        }
      } catch {
        // Non-critical fetch error
      } finally {
        if (alive) setIsCapturing(false);
      }
    };

    fetchSnapshot(false);

    return () => {
      alive = false;
      clearTimeout(pollTimerRef.current);
    };
  }, [sessionId, currentUrl, status]);

  // Execute supported browser actions (scroll, refresh)
  const handleAction = async (actionType) => {
    if (!sessionId || isCapturing || !currentUrl) return;
    try {
      setIsCapturing(true);
      setActionFeedback(actionType === 'scroll_down' ? 'Scrolling down...' : actionType === 'scroll_up' ? 'Scrolling up...' : 'Refreshing snapshot...');
      const res = await sendBrowserAction(sessionId, actionType);
      if (res?.screenshot_url) {
        setLatestScreenshotUrl(res.screenshot_url);
        setScreenshotAge(new Date());
        setLocalVerification('verified');
      }
      setTimeout(() => setActionFeedback(''), 2500);
    } catch (err) {
      console.warn('Browser action error:', err);
    } finally {
      setIsCapturing(false);
    }
  };

  const displayUrl = currentUrl || streamingUrl || '';
  const domainName = displayUrl.startsWith('http')
    ? displayUrl.split('/')[2]
    : displayUrl || 'Browser Ready';

  const hasScreenshot = !!latestScreenshotUrl;
  const isDenied = effectiveVerification === 'access_denied';
  const isAuth = effectiveVerification === 'auth_required';
  const isFailed = effectiveVerification === 'failed';

  return (
    <section className="browser-preview-panel" aria-label="Rendered Website Viewport">
      {/* ── Browser Chrome Header ─────────────────────────────────────── */}
      <div className="browser-topbar">
        <div className="browser-window-controls" aria-hidden="true">
          <span className="dot dot-close" />
          <span className="dot dot-minimize" />
          <span className="dot dot-maximize" />
        </div>

        <div className="browser-address-bar" role="region" aria-label="Current Website URL">
          <span className="ssl-lock" title="Secure connection">🔒</span>
          <span className="address-url" title={displayUrl || 'No active URL'}>
            {displayUrl ? (
              <span className="url-text">{displayUrl}</span>
            ) : (
              <span className="url-placeholder">Waiting for navigation command...</span>
            )}
          </span>

          {/* External HTTPS tab launcher */}
          {displayUrl && (
            <a
              href={displayUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="open-tab-btn"
              title="Open website directly in separate browser tab"
              aria-label={`Open ${displayUrl} in external tab`}
            >
              ↗ Open
            </a>
          )}
        </div>

        <div className="browser-meta-controls">
          {/* Action toolbar for supported browser actions */}
          {hasScreenshot && !isDenied && !isAuth && (
            <div className="browser-actions-toolbar" role="toolbar" aria-label="Snapshot controls">
              <button
                type="button"
                className="action-tool-btn"
                onClick={() => handleAction('scroll_down')}
                disabled={isCapturing}
                title="Scroll down and capture new snapshot"
              >
                ⬇ Scroll
              </button>
              <button
                type="button"
                className="action-tool-btn"
                onClick={() => handleAction('scroll_up')}
                disabled={isCapturing}
                title="Scroll up and capture new snapshot"
              >
                ⬆ Up
              </button>
              <button
                type="button"
                className="action-tool-btn"
                onClick={() => handleAction('refresh')}
                disabled={isCapturing}
                title="Capture fresh screenshot"
              >
                🔄
              </button>
            </div>
          )}

          {/* Verification status indicator badge */}
          {isDenied ? (
            <span className="verification-pill pill-denied" title="Access Denied by Server Security Policy">
              🚫 Access Denied
            </span>
          ) : isAuth ? (
            <span className="verification-pill pill-auth" title="Authentication / Login Required">
              🔐 Login Required
            </span>
          ) : hasScreenshot || effectiveVerification === 'verified' ? (
            <span className="verification-pill pill-verified" title="Verified Rendered Screenshot">
              ✓ Rendered
            </span>
          ) : null}

          <span className={`status-pill status-${status || 'idle'}`}>
            {isLoading || isCapturing
              ? 'Capturing...'
              : status === 'executing'
              ? 'Active'
              : 'Standby'}
          </span>
        </div>
      </div>

      {/* ── Navigation & Capture Progress Bar ────────────────────────────── */}
      {(isLoading || isCapturing) && (
        <div className="navigation-progress-bar" role="progressbar" aria-label="Page loading and capturing">
          <div className="progress-indicator" />
        </div>
      )}

      {/* ── Main Viewport (Screenshot-First) ──────────────────────────────── */}
      <div className="browser-viewport">

        {/* STATE 1: Server returned Access Denied (403, Akamai WAF, anti-bot) */}
        {isDenied && currentUrl ? (
          <div className="frame-fallback-overlay" role="alert">
            <div className="fallback-card fallback-card-denied">
              <span className="fallback-icon">🚫</span>
              <h4>Access Denied by Website</h4>
              <p>
                <strong>{domainName}</strong> restricted automated access via its server
                security policy (e.g. Akamai EdgeSuite / WAF bot protection).
              </p>
              <p className="fallback-sub">
                The website cannot be automated or embedded inside this preview window.
                You can open and browse the actual website directly in a separate browser tab.
              </p>
              <div className="fallback-actions">
                <a
                  href={currentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="direct-link-btn direct-link-primary"
                >
                  Open {domainName} in New Tab ↗
                </a>
              </div>
            </div>
          </div>

        /* STATE 2: Website requires authentication or CAPTCHA */
        ) : isAuth && currentUrl ? (
          <div className="frame-fallback-overlay" role="alert">
            <div className="fallback-card fallback-card-auth">
              <span className="fallback-icon">🔐</span>
              <h4>Authentication Required</h4>
              <p>
                <strong>{domainName}</strong> requires user authentication or CAPTCHA verification.
              </p>
              <p className="fallback-sub">
                For security, credentials and OTPs are not handled in the automated sandbox.
                Please sign in directly through your browser.
              </p>
              <div className="fallback-actions">
                <a
                  href={currentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="direct-link-btn direct-link-primary"
                >
                  Open {domainName} to Sign In ↗
                </a>
              </div>
            </div>
          </div>

        /* STATE 3: Navigation Failed */
        ) : isFailed && currentUrl && !hasScreenshot ? (
          <div className="frame-fallback-overlay" role="alert">
            <div className="fallback-card">
              <span className="fallback-icon">⚠️</span>
              <h4>Navigation Failed</h4>
              <p>
                Could not load <strong>{domainName}</strong>. {localMessage || 'The connection timed out or the URL was unreachable.'}
              </p>
              <div className="fallback-actions">
                <a
                  href={currentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="direct-link-btn direct-link-secondary"
                >
                  Open {domainName} ↗
                </a>
              </div>
            </div>
          </div>

        /* STATE 4: PRIMARY DISPLAY — Verified Rendered Screenshot */
        ) : hasScreenshot ? (
          <div className="screenshot-container">
            <div className="screenshot-badge">
              📸 Actual Website Rendered
              {screenshotAge && (
                <span className="screenshot-age">
                  &nbsp;· {Math.round((Date.now() - screenshotAge.getTime()) / 1000)}s ago
                </span>
              )}
            </div>

            <img
              key={latestScreenshotUrl.slice(-40)}
              src={latestScreenshotUrl}
              alt={`Rendered screenshot of ${domainName}`}
              className="browser-screenshot"
            />

            {/* Transparent read-only disclaimer */}
            <div className="screenshot-notice-bar" aria-hidden="true">
              {actionFeedback || '📸 Read-only preview snapshot · To interact directly, click Open ↗'}
            </div>
          </div>

        /* STATE 5: Loading initial screenshot */
        ) : currentUrl && (isLoading || isCapturing) ? (
          <div className="browser-empty-state">
            <div className="empty-content">
              <div className="empty-globe-icon" aria-hidden="true">⏳</div>
              <h3>Rendering Website...</h3>
              <p>Loading <strong>{domainName}</strong> and capturing a fresh snapshot.</p>
            </div>
          </div>

        /* STATE 6: Idle empty state */
        ) : (
          <div className="browser-empty-state">
            <div className="empty-content">
              <div className="empty-globe-icon" aria-hidden="true">🌐</div>
              <h3>Live Web Viewport</h3>
              <p>
                AwaazWeb will load and navigate actual websites here as you issue voice or
                text commands.
              </p>
              <div className="quick-suggestions">
                <span className="suggestion-label">Try commands like:</span>
                <code>"Delhi se Bhopal train dhundho"</code>
                <code>"Aaj ka mausam check karo"</code>
                <code>"Flipkart par headphones search karo"</code>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="browser-footer">
        <span className="browser-security-note">
          🔒 Agent Sandbox Active · Rendered Playwright Snapshot · Read-Only View
        </span>
        <span className="browser-zoom-indicator">100%</span>
      </footer>
    </section>
  );
}
