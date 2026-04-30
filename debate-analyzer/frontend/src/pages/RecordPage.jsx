import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAudioCapture } from '../hooks/useAudioCapture';
import { Waveform } from '../components/Waveform';
import { FileUploader } from '../components/FileUploader';

export function RecordPage() {
  const navigate = useNavigate();
  const [sessionId] = useState(() => crypto.randomUUID());
  const [elapsed, setElapsed] = useState(0);
  const [timerInterval, setTimerInterval] = useState(null);

  const [uploadError, setUploadError] = useState(null);

  const { state, error, chunkCount, analyserNode, startRecording, stopRecording } =
    useAudioCapture({
      onSilenceDetected: () => console.log('Auto-stop: silence detected')
    });

  useEffect(() => {
    if (state === 'recording') {
      const id = setInterval(() => setElapsed(e => e + 1), 1000);
      setTimerInterval(id);
    } else {
      clearInterval(timerInterval);
      if (state === 'stopped') navigate(`/session/${sessionId}`);
    }
  }, [state]);

  const formatTime = (s) => `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;

  const handleMicClick = () => {
    if (state === 'idle') startRecording(sessionId);
    else if (state === 'recording') stopRecording();
  };

  const micColor = state === 'recording' ? 'bg-coral-500 hover:bg-coral-600 shadow-[0_0_30px_rgba(244,63,94,0.5)]' : 'bg-teal-500 hover:bg-teal-600 shadow-[0_0_30px_rgba(20,184,166,0.5)]';
  const statusText = {
    idle: 'Tap to start recording',
    requesting_permission: 'Requesting microphone...',
    recording: `Recording — ${formatTime(elapsed)}`,
    stopping: 'Finishing up...',
    stopped: 'Processing your session...',
  }[state];

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-10 p-6 bg-slate-900 text-slate-100 font-sans selection:bg-teal-500/30">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-800 via-slate-900 to-black -z-10"></div>
      
      <div className="text-center space-y-3">
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-teal-400 to-emerald-300 bg-clip-text text-transparent drop-shadow-sm">
          Debate Analyzer v2
        </h1>
        <p className="text-slate-400 text-sm md:text-base max-w-md mx-auto">
          Capture your discussions and let AI extract insights, speaker summaries, and knowledge graphs.
        </p>
      </div>

      {(error || uploadError) && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm max-w-md w-full text-center">
          {error || uploadError}
        </div>
      )}

      <div className="h-24 flex items-center justify-center w-full">
        {state === 'recording' ? (
          <Waveform analyserNode={analyserNode} isRecording />
        ) : (
          <div className="h-20 w-full max-w-lg rounded-lg bg-slate-800/50 border border-slate-700/50 flex items-center justify-center">
            <span className="text-slate-600 text-sm tracking-widest uppercase">Waiting for audio</span>
          </div>
        )}
      </div>

      <button
        onClick={handleMicClick}
        disabled={['requesting_permission','stopping','stopped'].includes(state)}
        className={`w-32 h-32 rounded-full ${micColor} text-white shadow-lg
                    transition-all duration-300 ease-out flex items-center justify-center
                    disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95`}
      >
        {state === 'recording' ? (
          <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : (
          <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm0 13a6 6 0 006-6H6a6 6 0 006 6zm-1 4v2H9v2h6v-2h-2v-2h-2z"/>
          </svg>
        )}
      </button>

      <div className="text-center">
        <p className="text-slate-300 text-lg font-medium tracking-wide animate-pulse">{statusText}</p>
        {state === 'recording' && (
          <p className="text-slate-500 text-xs mt-2 font-mono bg-slate-800 py-1 px-2 rounded-md inline-block">
            {chunkCount} chunks streamed
          </p>
        )}
      </div>

      {state === 'idle' && (
        <>
          <div className="flex items-center gap-4 w-full max-w-xs py-4">
            <div className="h-[1px] flex-1 bg-slate-800"></div>
            <span className="text-slate-600 text-[10px] font-bold uppercase tracking-widest">OR</span>
            <div className="h-[1px] flex-1 bg-slate-800"></div>
          </div>

          <FileUploader 
            onUploadStart={() => setUploadError(null)}
            onUploadSuccess={(data) => navigate(`/session/${data.session_id}`)}
            onUploadError={(msg) => setUploadError(msg)}
          />
        </>
      )}
    </div>
  );
}
