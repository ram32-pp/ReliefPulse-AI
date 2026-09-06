'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/lib/i18n';
import { useVideoRecorder } from '@/hooks/useVideoRecorder';
import {
  Camera,
  Video,
  StopCircle,
  RefreshCw,
  FlipHorizontal,
  CheckCircle2,
  AlertCircle,
  UploadCloud,
  FolderUp,
  Image as ImageIcon,
  Film,
  Trash2,
  Smartphone,
} from 'lucide-react';

interface VideoRecorderProps {
  onVideoCaptured?: (
    blob: Blob | null,
    url: string | null,
    snapshotUrl: string | null,
    snapshotBlob?: Blob | null
  ) => void;
  className?: string;
}

export const VideoRecorder: React.FC<VideoRecorderProps> = ({ onVideoCaptured, className = '' }) => {
  const { t } = useTranslation();
  const {
    isRecording,
    recordingTime,
    videoBlob,
    videoUrl,
    snapshotBlob,
    snapshotUrl,
    isCameraActive,
    error,
    facingMode,
    setVideoRef,
    startCamera,
    stopCamera,
    startRecording,
    stopRecording,
    takeSnapshot,
    switchCamera,
    resetRecording,
    setUploadedFile,
  } = useVideoRecorder();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const nativeCameraInputRef = useRef<HTMLInputElement>(null);
  const callbackRef = useRef(onVideoCaptured);
  callbackRef.current = onVideoCaptured;

  // Auto-start camera when the component mounts if not already captured
  useEffect(() => {
    if (!videoUrl && !snapshotUrl && !isCameraActive) {
      startCamera().catch((err) => {
        console.log('[VideoRecorder] Initial auto-start camera info:', err);
      });
    }
  }, []);

  // Notify parent whenever visual media state updates
  useEffect(() => {
    if (callbackRef.current) {
      callbackRef.current(videoBlob, videoUrl, snapshotUrl, snapshotBlob);
    }
  }, [videoBlob, videoUrl, snapshotUrl, snapshotBlob]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
    }
    // reset input value so re-selecting the same file triggers onChange
    e.target.value = '';
  };

  const handleTakeSnapshot = () => {
    const res = takeSnapshot();
    if (res) {
      stopCamera();
    }
  };

  return (
    <div
      className={`w-full rounded-3xl overflow-hidden glass border border-white/15 p-4 sm:p-5 shadow-2xl relative ${className}`}
    >
      {/* Hidden File Input for Device Upload (Images + Videos) */}
      <input
        id="recorder-file-upload"
        name="recorder-file-upload"
        type="file"
        ref={fileInputRef}
        accept="image/*,video/*"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Hidden Mobile Native Camera Input Fallback */}
      <input
        id="recorder-native-camera"
        name="recorder-native-camera"
        type="file"
        ref={nativeCameraInputRef}
        accept="image/*,video/*"
        capture="environment"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Top Header Controls */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="p-2.5 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <Video size={20} />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-warm-white flex items-center gap-2">
              {t('step_3_title')}
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-pulse-red/20 text-pulse-red border border-pulse-red/30">
                LIVE / UPLOAD
              </span>
            </h3>
            <p className="text-xs text-slate-400">Capture photo/video or upload directly from files</p>
          </div>
        </div>

        {/* Header Right Action Buttons */}
        <div className="flex items-center gap-2">
          {isCameraActive && !videoUrl && !snapshotUrl && (
            <button
              onClick={switchCamera}
              title={t('flip_camera')}
              className="p-2 sm:px-3 sm:py-2 rounded-xl bg-white/10 hover:bg-white/20 text-slate-200 transition-all border border-white/10 active:scale-95 flex items-center gap-1.5 text-xs font-medium cursor-pointer"
            >
              <FlipHorizontal size={15} />
              <span className="hidden sm:inline">{facingMode === 'environment' ? 'Rear' : 'Front'}</span>
            </button>
          )}

          {/* Always Available Upload Button in Header */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-2 rounded-xl bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue border border-sky-blue/40 text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95 cursor-pointer"
            title="Upload from Device"
          >
            <UploadCloud size={15} />
            <span>Upload</span>
          </button>
        </div>
      </div>

      {/* Main Viewport Container */}
      <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-slate-950 border border-white/10 shadow-inner flex items-center justify-center">
        {/* State 1: Active Live Camera */}
        {isCameraActive && !videoUrl && !snapshotUrl && (
          <div className="relative w-full h-full">
            <video
              ref={setVideoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover ${facingMode === 'user' ? 'scale-x-[-1]' : ''}`}
            />

            {/* Cyber HUD Framing Corner Overlays */}
            <div className="absolute top-3 left-3 w-6 h-6 hud-corner-tl pointer-events-none"></div>
            <div className="absolute top-3 right-3 w-6 h-6 hud-corner-tr pointer-events-none"></div>
            <div className="absolute bottom-3 left-3 w-6 h-6 hud-corner-bl pointer-events-none"></div>
            <div className="absolute bottom-3 right-3 w-6 h-6 hud-corner-br pointer-events-none"></div>

            {/* Center HUD Reticle */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-12 h-12 rounded-full border border-sky-blue/30 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-sky-blue/60 animate-ping"></div>
              </div>
            </div>

            {/* Live Recording HUD Status */}
            {isRecording ? (
              <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-pulse-red/90 text-white font-mono text-xs font-bold shadow-lg animate-pulse backdrop-blur-md">
                <span className="w-2.5 h-2.5 rounded-full bg-white animate-ping"></span>
                REC {formatTime(recordingTime)}
              </div>
            ) : (
              <div className="absolute top-4 left-4 flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/80 text-relief-green text-xs font-semibold backdrop-blur-md border border-relief-green/30">
                <span className="w-2 h-2 rounded-full bg-relief-green animate-pulse"></span>
                {t('camera_live')}
              </div>
            )}
          </div>
        )}

        {/* State 2: Video Playback Preview */}
        {videoUrl && (
          <div className="relative w-full h-full bg-black flex items-center justify-center">
            <video
              src={videoUrl}
              controls
              playsInline
              controlsList="nodownload"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-3 right-3 rtl:left-3 rtl:right-auto px-3 py-1.5 rounded-full bg-relief-green/20 border border-relief-green/40 text-relief-green text-xs font-bold flex items-center gap-1.5 backdrop-blur-md shadow-lg">
              <CheckCircle2 size={15} />
              <span>Video Ready for AI</span>
            </div>
          </div>
        )}

        {/* State 3: Snapshot Photo Preview */}
        {snapshotUrl && !videoUrl && (
          <div className="relative w-full h-full bg-black flex items-center justify-center">
            <img
              src={snapshotUrl}
              alt="Disaster evidence snapshot"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-3 right-3 rtl:left-3 rtl:right-auto px-3 py-1.5 rounded-full bg-sky-blue/20 border border-sky-blue/40 text-sky-blue text-xs font-bold flex items-center gap-1.5 backdrop-blur-md shadow-lg">
              <ImageIcon size={15} />
              <span>Photo Ready for AI</span>
            </div>
          </div>
        )}

        {/* State 4: Camera Off / Standby Prompt */}
        {!isCameraActive && !videoUrl && !snapshotUrl && (
          <div className="flex flex-col items-center justify-center p-6 text-center z-10 w-full max-w-md">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mb-3 text-sky-blue shadow-lg">
              <Camera size={40} className="animate-pulse" />
            </div>
            <h4 className="text-base sm:text-lg font-bold text-warm-white mb-1">
              Capture or Upload Visual Evidence
            </h4>
            <p className="text-xs text-slate-400 max-w-sm mb-5 leading-relaxed">
              Take photos and videos using your camera, or upload image and video files directly from your device.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-3 w-full justify-center">
              {/* Primary Start Camera Button */}
              <button
                onClick={startCamera}
                className="w-full sm:w-auto px-5 py-3 rounded-2xl bg-gradient-to-r from-pulse-red to-rose-600 hover:from-red-600 hover:to-rose-700 text-white font-bold text-xs shadow-lg hover:shadow-pulse-red/30 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
              >
                <Video size={16} />
                <span>{t('start_camera')}</span>
              </button>

              {/* Dedicated Upload Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full sm:w-auto px-5 py-3 rounded-2xl bg-sky-blue hover:bg-sky-400 text-slate-950 font-bold text-xs shadow-lg transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
              >
                <FolderUp size={16} />
                <span>Upload Image / Video</span>
              </button>
            </div>

            {/* Mobile Native Camera Shortcut */}
            <div className="mt-3">
              <button
                onClick={() => nativeCameraInputRef.current?.click()}
                className="text-[11px] text-slate-400 hover:text-sky-blue flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Smartphone size={13} />
                <span>Use Mobile Native Camera App</span>
              </button>
            </div>
          </div>
        )}

        {/* Error Notification Banner */}
        {error && !videoUrl && !snapshotUrl && (
          <div className="absolute bottom-3 left-3 right-3 p-3 rounded-xl bg-red-950/95 border border-red-500/50 text-red-200 text-xs flex items-center justify-between gap-3 backdrop-blur-md z-20 shadow-xl">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="shrink-0 text-red-400" />
              <span className="leading-snug">{error}</span>
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-1.5 rounded-lg bg-sky-blue text-slate-950 font-bold text-[11px] shrink-0 active:scale-95 cursor-pointer"
            >
              Upload Files Instead
            </button>
          </div>
        )}
      </div>

      {/* Control Action Buttons Footer */}
      <div className="mt-4">
        {/* Active Camera Action Controls */}
        {isCameraActive && !videoUrl && !snapshotUrl && (
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            {/* Take Photo Button */}
            <button
              onClick={handleTakeSnapshot}
              className="flex-1 min-w-[120px] py-3 px-3 rounded-xl bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue border border-sky-blue/40 text-xs font-bold transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer shadow-md"
            >
              <Camera size={16} />
              <span>{t('take_photo')}</span>
            </button>

            {/* Start / Stop Video Recording */}
            {!isRecording ? (
              <button
                onClick={startRecording}
                className="flex-1 min-w-[130px] py-3 px-3 rounded-xl bg-pulse-red hover:bg-red-600 text-white text-xs font-bold transition-all shadow-lg hover:shadow-pulse-red/40 flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
              >
                <Video size={16} />
                <span>{t('start_recording')}</span>
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="flex-1 min-w-[130px] py-3 px-3 rounded-xl bg-amber-alert hover:bg-amber-600 text-black text-xs font-bold transition-all shadow-lg flex items-center justify-center gap-2 active:scale-95 animate-pulse cursor-pointer"
              >
                <StopCircle size={16} />
                <span>{t('stop_recording')} ({formatTime(recordingTime)})</span>
              </button>
            )}

            {/* Direct Upload Media Button while Camera is Active */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="py-3 px-3.5 rounded-xl bg-white/10 hover:bg-white/20 text-slate-200 border border-white/15 text-xs font-bold transition-all flex items-center justify-center gap-1.5 active:scale-95 cursor-pointer"
              title="Upload Image/Video from Files"
            >
              <FolderUp size={16} />
              <span className="hidden sm:inline">Upload Files</span>
            </button>

            {/* Stop Camera Toggle */}
            <button
              onClick={stopCamera}
              className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white border border-white/10 text-xs transition-all cursor-pointer"
              title={t('stop_camera')}
            >
              <span className="sr-only">{t('stop_camera')}</span>
              <StopCircle size={16} />
            </button>
          </div>
        )}

        {/* Media Captured Review Actions */}
        {(videoUrl || snapshotUrl) && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-2xl bg-slate-900/90 border border-white/10">
            <div className="flex items-center gap-2 text-xs font-bold text-relief-green">
              <CheckCircle2 size={18} />
              <span>
                {videoUrl ? 'Incident Video Attached' : 'Incident Photo Attached'}
              </span>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              {/* Retake / Restart Camera Button */}
              <button
                onClick={() => {
                  resetRecording();
                  startCamera();
                }}
                className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-slate-200 border border-white/15 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer active:scale-95"
              >
                <RefreshCw size={14} />
                <span>Retake / Camera</span>
              </button>

              {/* Upload Different File Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue border border-sky-blue/30 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer active:scale-95"
              >
                <FolderUp size={14} />
                <span>Upload Another</span>
              </button>

              {/* Clear Evidence */}
              <button
                onClick={resetRecording}
                className="p-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs transition-all cursor-pointer"
                title="Remove evidence"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoRecorder;
