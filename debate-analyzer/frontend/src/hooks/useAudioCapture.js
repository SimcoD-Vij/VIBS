/**
 * useAudioCapture — custom React hook
 *
 * Manages the full recording lifecycle:
 *   idle → requesting_permission → recording → stopping → stopped
 *
 * Exposes:
 *   state:      current lifecycle phase (string)
 *   startRecording(sessionId): opens mic, connects WS, begins chunking
 *   stopRecording():           sends stop signal, closes WS gracefully
 *   analyserNode:              Web Audio API AnalyserNode for waveform drawing
 *   error:                     string | null
 *   chunkCount:                number of chunks sent so far
 *   onSilenceDetected:        callback set by parent — called when server sends vad_silence
 */
import { useState, useRef, useCallback } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useAudioCapture({ onSilenceDetected } = {}) {
  const [state, setState] = useState('idle');
  const [error, setError] = useState(null);
  const [chunkCount, setChunkCount] = useState(0);
  const [analyserNode, setAnalyserNode] = useState(null);

  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);

  const startRecording = useCallback(async (sessionId) => {
    try {
      setState('requesting_permission');

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });
      streamRef.current = stream;

      // Set up Web Audio API analyser for the waveform visualisation
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioCtxRef.current = audioCtx;
      setAnalyserNode(analyser);

      // Connect WebSocket
      const ws = new WebSocket(`${WS_URL}/ws/session/${sessionId}`);
      ws.binaryType = 'blob';
      wsRef.current = ws;

      ws.onopen = () => {
        // Start MediaRecorder after WebSocket is ready
        const recorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm;codecs=opus',
          audioBitsPerSecond: 64000,
        });
        recorderRef.current = recorder;

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(event.data);
            setChunkCount(prev => prev + 1);
          }
        };

        recorder.start(5000); // Chunk every 5 seconds
        setState('recording');
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'vad_silence') {
          onSilenceDetected?.();
          stopRecording();
        }
      };

      ws.onerror = () => setError('WebSocket connection failed');

    } catch (err) {
      setError(err.message);
      setState('idle');
    }
  }, [onSilenceDetected]);

  const stopRecording = useCallback(() => {
    setState('stopping');

    if (recorderRef.current?.state !== 'inactive') {
      recorderRef.current?.stop();
    }
    streamRef.current?.getTracks().forEach(t => t.stop());

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop' }));
      wsRef.current.close();
    }

    audioCtxRef.current?.close();
    setState('stopped');
  }, []);

  return { state, error, chunkCount, analyserNode, startRecording, stopRecording };
}
