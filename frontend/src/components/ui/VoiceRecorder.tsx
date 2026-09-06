'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from '@/lib/i18n';
import { Mic, Square, Play, Pause, RotateCcw, Volume2, CheckCircle2, AlertCircle } from 'lucide-react';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';

interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob | null) => void;
  className?: string;
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  onRecordingComplete,
  className = '',
}) => {
  const { t } = useTranslation();
  const {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
    audioUrl,
    duration,
    waveform,
    reset,
  } = useVoiceRecorder();

  // Audio Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackTime, setPlaybackTime] = useState(0);
  const [playbackDuration, setPlaybackDuration] = useState(0);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Hold-to-Record support
  const holdTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isHoldModeRef = useRef<boolean>(false);

  const handlePointerDown = () => {
    if (audioBlob) return;
    isHoldModeRef.current = false;
    holdTimerRef.current = setTimeout(() => {
      isHoldModeRef.current = true;
      if (!isRecording) {
        startRecording();
      }
    }, 250);
  };

  const handlePointerUp = () => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    if (isHoldModeRef.current && isRecording) {
      stopRecording();
      isHoldModeRef.current = false;
    }
  };

  // Sync recording completion to parent
  useEffect(() => {
    onRecordingComplete(audioBlob);
  }, [audioBlob, onRecordingComplete]);

  // Handle Play/Pause
  const togglePlayPause = () => {
    if (!audioPlayerRef.current || !audioUrl) return;

    if (isPlaying) {
      audioPlayerRef.current.pause();
      setIsPlaying(false);
    } else {
      audioPlayerRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.warn('Audio playback error:', err));
    }
  };

  // Handle Reset / Re-record
  const handleReset = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setPlaybackTime(0);
    setPlaybackDuration(0);
    reset();
    onRecordingComplete(null);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`flex flex-col items-center w-full max-w-lg mx-auto py-2 ${className}`}>
      {/* Hidden Audio Element for Playback */}
      {audioUrl && (
        <audio
          ref={audioPlayerRef}
          src={audioUrl}
          onLoadedMetadata={(e) => {
            const d = e.currentTarget.duration;
            if (!isNaN(d) && isFinite(d)) {
              setPlaybackDuration(d);
            }
          }}
          onTimeUpdate={(e) => {
            setPlaybackTime(e.currentTarget.currentTime);
          }}
          onEnded={() => {
            setIsPlaying(false);
            setPlaybackTime(0);
          }}
        />
      )}

      {/* Waveform Display Container */}
      <div className="h-20 w-full flex items-center justify-center gap-1 mb-5 px-4 bg-slate-950/80 rounded-2xl border border-white/10 overflow-hidden shadow-inner">
        {isRecording ? (
          <div className="w-full h-full flex items-center justify-center gap-1.5 py-2">
            {waveform.length > 0 ? (
              waveform.map((val, i) => (
                <div
                  key={i}
                  className="w-1.5 sm:w-2 bg-gradient-to-t from-pulse-red via-rose-500 to-amber-alert rounded-full transition-all duration-75 shadow-[0_0_10px_rgba(255,42,76,0.5)]"
                  style={{ height: `${Math.max(12, val * 100)}%` }}
                />
              ))
            ) : (
              <div className="text-xs text-amber-alert font-mono animate-pulse">
                Detecting acoustic distress vibrations...
              </div>
            )}
          </div>
        ) : audioBlob ? (
          /* Recorded Audio Playback Waveform Bar */
          <div className="w-full flex items-center justify-between gap-4 px-2">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={togglePlayPause}
                className="w-12 h-12 rounded-xl bg-gradient-to-tr from-sky-blue to-cyan-400 text-slate-950 flex items-center justify-center shadow-lg shadow-sky-blue/30 active:scale-95 transition-all cursor-pointer"
                aria-label={isPlaying ? 'Pause' : 'Play audio note'}
              >
                {isPlaying ? <Pause size={20} className="fill-current" /> : <Play size={20} className="fill-current ml-0.5" />}
              </button>
              <div>
                <span className="text-xs font-bold text-warm-white flex items-center gap-1.5">
                  <Volume2 size={15} className="text-sky-blue" />
                  Voice Distress Recording
                </span>
                <span className="text-[11px] font-mono text-slate-400 block mt-0.5">
                  {formatTime(playbackTime)} / {formatTime(playbackDuration || duration || 1)}
                </span>
              </div>
            </div>

            {/* Playback progress tracker */}
            <div className="flex-grow max-w-[140px] sm:max-w-[180px]">
              <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-sky-blue to-relief-green rounded-full transition-all duration-100"
                  style={{
                    width: `${
                      playbackDuration > 0
                        ? (playbackTime / playbackDuration) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white transition-all cursor-pointer border border-white/10"
              title="Delete & Re-record"
            >
              <RotateCcw size={16} />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center">
            <div className="h-[2px] w-48 bg-gradient-to-r from-transparent via-white/25 to-transparent mb-2" />
            <span className="text-[11px] font-mono text-slate-400">
              Ultra-low bandwidth • Works during 2G/3G network congestion
            </span>
          </div>
        )}
      </div>

      {/* Main Mic Button or Re-record Control */}
      {!audioBlob ? (
        <div className="flex flex-col items-center">
          <div className="relative">
            {isRecording && (
              <>
                <div className="absolute -inset-4 rounded-full bg-pulse-red/30 animate-ping pointer-events-none" />
                <div className="absolute -inset-8 rounded-full bg-pulse-red/10 animate-pulse pointer-events-none" />
              </>
            )}
            <button
              type="button"
              onPointerDown={handlePointerDown}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
              onClick={() => {
                if (!isHoldModeRef.current) {
                  isRecording ? stopRecording() : startRecording();
                }
                isHoldModeRef.current = false;
              }}
              className={`w-24 h-24 rounded-full flex items-center justify-center shadow-[0_10px_35px_rgba(0,0,0,0.5)] transition-all duration-300 active:scale-95 border-2 cursor-pointer select-none touch-none ${
                isRecording
                  ? 'bg-gradient-to-tr from-amber-alert to-amber-500 text-slate-950 border-white shadow-amber-alert/50 animate-pulse'
                  : 'bg-gradient-to-tr from-[#DC2626] to-rose-700 text-white border-white/50 shadow-[#DC2626]/50 hover:scale-105'
              }`}
              aria-label={isRecording ? 'Stop Recording' : 'Hold or Tap to Record'}
            >
              {isRecording ? (
                <Square size={34} className="fill-current" />
              ) : (
                <Mic size={38} className="transition-transform group-hover:scale-110" />
              )}
            </button>
          </div>

          <div className="mt-4 text-center">
            {isRecording ? (
              <div className="flex flex-col items-center">
                <span className="font-mono text-2xl font-black text-pulse-red tracking-wider animate-pulse">
                  {formatTime(duration)} / 01:00
                </span>
                <span className="text-xs text-amber-alert font-bold mt-1 uppercase tracking-wide">
                  RELEASE OR TAP TO FINISH RECORDING
                </span>
              </div>
            ) : (
              <div>
                <span className="font-black text-base sm:text-lg text-warm-white tracking-wide block">
                  HOLD OR TAP TO RECORD VOICE SOS
                </span>
                <p className="text-xs text-slate-300 mt-1">
                  Urdu, English, Regional dialects • Release or tap to finish
                </p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Status Card after Recording Complete */
        <div className="w-full flex flex-col items-center">
          <div className="w-full p-3.5 rounded-2xl bg-relief-green/15 border border-relief-green/30 text-relief-green text-xs font-bold flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={18} />
              <span>Voice Note Ready for Verification ({((audioBlob.size || 0) / 1024).toFixed(1)} KB)</span>
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-slate-300 hover:text-white underline font-semibold cursor-pointer"
            >
              Re-record
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceRecorder;
