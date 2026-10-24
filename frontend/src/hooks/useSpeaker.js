import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook for speech synthesis, auto-selecting Hindi (hi-IN) voice if available.
 */
export function useSpeaker() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [hindiVoice, setHindiVoice] = useState(null);
  const synthRef = useRef(typeof window !== 'undefined' ? window.speechSynthesis : null);

  const loadVoices = useCallback(() => {
    if (!synthRef.current) return;
    const voices = synthRef.current.getVoices();
    // Look for hi-IN or Indian English / Hindi voice
    const foundHindi =
      voices.find((v) => v.lang === 'hi-IN' || v.lang === 'hi_IN') ||
      voices.find((v) => v.lang.startsWith('hi')) ||
      voices.find((v) => v.lang === 'en-IN');
    if (foundHindi) {
      setHindiVoice(foundHindi);
    }
  }, []);

  useEffect(() => {
    if (!synthRef.current) return;
    loadVoices();
    if (synthRef.current.onvoiceschanged !== undefined) {
      synthRef.current.onvoiceschanged = loadVoices;
    }
  }, [loadVoices]);

  const speak = useCallback(
    (text, onEnd) => {
      if (!synthRef.current) return;
      synthRef.current.cancel(); // Stop prior speech

      const utterance = new SpeechSynthesisUtterance(text);
      if (hindiVoice) {
        utterance.voice = hindiVoice;
      }
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => {
        setIsSpeaking(false);
        if (onEnd) onEnd();
      };
      utterance.onerror = (e) => {
        console.error('Speech synthesis error:', e);
        setIsSpeaking(false);
        if (onEnd) onEnd();
      };

      synthRef.current.speak(utterance);
    },
    [hindiVoice]
  );

  const stop = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  }, []);

  return {
    isSpeaking,
    speak,
    stop,
    hindiVoice,
  };
}
