'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob, durationSec: number) => void;
  maxDurationSec?: number;
  disabled?: boolean;
}

type RecorderState = 'idle' | 'recording' | 'stopped';

export default function VoiceRecorder({
  onRecordingComplete,
  maxDurationSec = 300,
  disabled = false,
}: VoiceRecorderProps) {
  const [state, setState] = useState<RecorderState>('idle');
  const [elapsed, setElapsed] = useState(0);
  const [sizeBytesEstimate, setSizeBytesEstimate] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Waveform animation
  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const barCount = 40;
    const barWidth = Math.floor(w / barCount) - 2;
    const step = Math.floor(bufferLength / barCount);

    for (let i = 0; i < barCount; i++) {
      const value = dataArray[i * step] / 255;
      const barH = Math.max(4, value * h);
      const x = i * (barWidth + 2);
      const y = (h - barH) / 2;

      const gradient = ctx.createLinearGradient(0, y, 0, y + barH);
      gradient.addColorStop(0, '#8b5cf6');
      gradient.addColorStop(1, '#3b82f6');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barH, 2);
      ctx.fill();
    }

    animFrameRef.current = requestAnimationFrame(drawWaveform);
  }, []);

  const stopAnimation = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = 0;
    }
    // Clear canvas
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    stopAnimation();

    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
  }, [stopAnimation]);

  // Auto-stop at maxDurationSec
  useEffect(() => {
    if (state === 'recording' && elapsed >= maxDurationSec) {
      stopRecording();
    }
  }, [elapsed, maxDurationSec, state, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAnimation();
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, [stopAnimation]);

  const startRecording = async () => {
    setError(null);
    chunksRef.current = [];
    setSizeBytesEstimate(0);
    setElapsed(0);

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
    } catch {
      setError('Microphone access denied. Please allow microphone access and try again.');
      return;
    }

    // Set up audio analyser for waveform
    try {
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
    } catch {
      // Non-fatal — continue without waveform
      analyserRef.current = null;
    }

    // Pick best supported MIME type
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : '';

    const options = mimeType ? { mimeType } : undefined;
    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream, options);
    } catch {
      recorder = new MediaRecorder(stream);
    }

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
        setSizeBytesEstimate(prev => prev + e.data.size);
      }
    };

    recorder.onstop = () => {
      setState('stopped');
      stream.getTracks().forEach(t => t.stop());
      streamRef.current = null;

      const finalBlob = new Blob(chunksRef.current, { type: mimeType || 'audio/webm' });
      const durationSec = Math.round((Date.now() - startTimeRef.current) / 1000);
      onRecordingComplete(finalBlob, durationSec);
    };

    mediaRecorderRef.current = recorder;
    recorder.start(500); // collect chunks every 500ms
    startTimeRef.current = Date.now();
    setState('recording');

    timerRef.current = setInterval(() => {
      setElapsed(Math.round((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    if (analyserRef.current) {
      drawWaveform();
    }
  };

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="flex flex-col items-center gap-4 w-full">
      {error && (
        <div className="w-full bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Waveform canvas */}
      <canvas
        ref={canvasRef}
        width={360}
        height={80}
        className={`rounded-xl transition-opacity duration-300 ${state === 'recording' ? 'opacity-100' : 'opacity-0'}`}
      />

      {/* Timer */}
      {state === 'recording' && (
        <div className="flex flex-col items-center gap-1">
          <span className="text-3xl font-mono font-bold text-white tabular-nums">
            {formatTime(elapsed)}
          </span>
          <span className="text-xs text-gray-500">
            {formatSize(sizeBytesEstimate)} · max {formatTime(maxDurationSec)}
          </span>
        </div>
      )}

      {/* Buttons */}
      {state === 'idle' && (
        <button
          onClick={startRecording}
          disabled={disabled}
          className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-8 py-4 rounded-2xl text-lg transition-all shadow-lg shadow-violet-500/20"
        >
          <span className="text-2xl">🎙</span> Start Recording
        </button>
      )}

      {state === 'recording' && (
        <button
          onClick={stopRecording}
          className="flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white font-semibold px-8 py-4 rounded-2xl text-lg transition-all animate-pulse"
        >
          <span className="inline-block w-3 h-3 bg-white rounded-sm" /> Stop &amp; Build Resume
        </button>
      )}
    </div>
  );
}
