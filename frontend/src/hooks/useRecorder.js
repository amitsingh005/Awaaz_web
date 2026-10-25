import { useState, useRef, useCallback } from 'react';

/**
 * Gets the best audio MIME type supported by the browser.
 */
function getSupportedMimeType() {
  if (typeof MediaRecorder === 'undefined') return '';
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
    'audio/aac',
    '',
  ];
  for (const mime of candidates) {
    if (!mime || MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return '';
}

/**
 * Hook for capturing audio from user's microphone using MediaRecorder API.
 * Includes permission handling, format selection, and descriptive error reporting.
 */
export function useRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [permissionStatus, setPermissionStatus] = useState('idle'); // idle | requesting | granted | denied
  const [audioBlob, setAudioBlob] = useState(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = useCallback(async () => {
    chunksRef.current = [];
    setIsPreparing(true);
    setPermissionStatus('requesting');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setIsPreparing(false);
      setPermissionStatus('denied');
      throw new Error('Aapke browser mein microphone support upalabdha nahi hai.');
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;
      setPermissionStatus('granted');

      const mimeType = getSupportedMimeType();
      const options = mimeType ? { mimeType } : undefined;
      const recorder = new MediaRecorder(stream, options);

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const type = mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type });
        setAudioBlob(blob);

        // Stop all tracks to turn off mic hardware LED indicator
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
      };

      recorder.start(100); // 100ms slice
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setIsPreparing(false);
    } catch (err) {
      setIsPreparing(false);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setPermissionStatus('denied');
        throw new Error('Microphone permission block hai. Kripya browser address bar mein jakar permission allow karein.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        throw new Error('Koi microphone nahi mila. Kripya mic connect karein.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        throw new Error('Microphone kisi aur app mein vyast hai.');
      }
      throw err;
    }
  }, []);

  const stopRecording = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        setIsRecording(false);
        setIsPreparing(false);
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const mimeType = getSupportedMimeType() || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        setIsRecording(false);
        setIsPreparing(false);

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  return {
    isRecording,
    isPreparing,
    permissionStatus,
    audioBlob,
    startRecording,
    stopRecording,
  };
}
