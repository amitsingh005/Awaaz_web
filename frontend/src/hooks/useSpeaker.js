import { useState, useCallback, useRef, useEffect } from 'react';
import { convertTextToSpeech } from '../services/api';

/**
 * Converts a base64 encoded audio string to an Object URL for playback.
 */
function base64ToBlobUrl(b64, mimeType = 'audio/wav') {
  const byteCharacters = atob(b64);
  const byteNumbers = new Uint8Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const blob = new Blob([byteNumbers], { type: mimeType });
  return URL.createObjectURL(blob);
}

/**
 * Hook for playing speech responses using Sarvam AI Bulbul TTS.
 * Plays backend-generated audio seamlessly with fallback handling.
 */
export function useSpeaker() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoadingTTS, setIsLoadingTTS] = useState(false);
  const audioRef = useRef(null);
  const currentBlobUrlRef = useRef(null);

  const cleanupAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current = null;
    }
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current);
      currentBlobUrlRef.current = null;
    }
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, []);

  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, [cleanupAudio]);

  const stop = useCallback(() => {
    cleanupAudio();
    setIsSpeaking(false);
    setIsLoadingTTS(false);
  }, [cleanupAudio]);

  /**
   * Plays audio from base64 string or fetches from Sarvam TTS backend endpoint.
   * @param {string|{text: string, audioBase64?: string}} input
   * @param {() => void} [onEnd]
   */
  const speak = useCallback(
    async (input, onEnd) => {
      // Stop previous audio first
      stop();

      const text = typeof input === 'string' ? input : input?.text || '';
      const preloadedB64 = typeof input === 'object' ? input?.audioBase64 : null;

      if (!text && !preloadedB64) return;

      try {
        let audioUrl = null;

        if (preloadedB64) {
          // Fast-path: use pre-generated Sarvam audio returned in response
          audioUrl = base64ToBlobUrl(preloadedB64, 'audio/wav');
        } else {
          // Fetch on-demand from Sarvam TTS endpoint
          setIsLoadingTTS(true);
          const audioBlob = await convertTextToSpeech(text, {
            languageCode: 'hi-IN',
            speaker: 'shubh',
          });
          audioUrl = URL.createObjectURL(audioBlob);
          setIsLoadingTTS(false);
        }

        currentBlobUrlRef.current = audioUrl;
        const audio = new Audio(audioUrl);
        audioRef.current = audio;

        audio.onplay = () => {
          setIsSpeaking(true);
        };

        audio.onended = () => {
          setIsSpeaking(false);
          cleanupAudio();
          if (onEnd) onEnd();
        };

        audio.onerror = (e) => {
          console.error('Sarvam audio playback error:', e);
          setIsSpeaking(false);
          cleanupAudio();

          // Graceful fallback to browser speech synthesis if audio playback fails
          if (typeof window !== 'undefined' && window.speechSynthesis && text) {
            const fallbackUtterance = new SpeechSynthesisUtterance(text);
            fallbackUtterance.lang = 'hi-IN';
            fallbackUtterance.onend = () => {
              if (onEnd) onEnd();
            };
            window.speechSynthesis.speak(fallbackUtterance);
          } else if (onEnd) {
            onEnd();
          }
        };

        await audio.play();
      } catch (err) {
        console.error('Failed to play Sarvam TTS response:', err);
        setIsLoadingTTS(false);
        setIsSpeaking(false);
        cleanupAudio();

        // Browser fallback
        if (typeof window !== 'undefined' && window.speechSynthesis && text) {
          const fallbackUtterance = new SpeechSynthesisUtterance(text);
          fallbackUtterance.lang = 'hi-IN';
          fallbackUtterance.onend = () => {
            if (onEnd) onEnd();
          };
          window.speechSynthesis.speak(fallbackUtterance);
        } else if (onEnd) {
          onEnd();
        }
      }
    },
    [cleanupAudio, stop]
  );

  return {
    isSpeaking,
    isLoadingTTS,
    speak,
    stop,
    engineName: 'Sarvam AI Bulbul (v3)',
  };
}
