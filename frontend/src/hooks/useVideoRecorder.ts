'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

export interface UseVideoRecorderReturn {
  isRecording: boolean;
  recordingTime: number;
  videoBlob: Blob | null;
  videoUrl: string | null;
  snapshotBlob: Blob | null;
  snapshotUrl: string | null;
  isCameraActive: boolean;
  hasPermission: boolean | null;
  error: string | null;
  facingMode: 'environment' | 'user';
  videoRef: React.RefObject<HTMLVideoElement | null>;
  setVideoRef: (node: HTMLVideoElement | null) => void;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  startRecording: () => void;
  stopRecording: () => void;
  takeSnapshot: () => { blob: Blob; url: string } | null;
  switchCamera: () => void;
  resetRecording: () => void;
  setUploadedFile: (file: File) => void;
  mediaSource: 'live_camera' | 'gallery_unverified' | null;
}

function dataURLtoBlob(dataurl: string): Blob {
  const arr = dataurl.split(',');
  const mimeMatch = arr[0].match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new Blob([u8arr], { type: mime });
}

export function useVideoRecorder(): UseVideoRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [snapshotBlob, setSnapshotBlob] = useState<Blob | null>(null);
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const [mediaSource, setMediaSource] = useState<'live_camera' | 'gallery_unverified' | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Stop active media stream tracks
  const stopCamera = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (e) {
          // ignore
        }
      });
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
  }, []);

  // Callback ref: immediately attaches the stream as soon as <video> mounts into DOM
  const setVideoRef = useCallback((node: HTMLVideoElement | null) => {
    videoRef.current = node;
    if (node && mediaStreamRef.current) {
      node.srcObject = mediaStreamRef.current;
      node.muted = true;
      node.play().catch((e) => console.warn('[useVideoRecorder] Video play error in setVideoRef:', e));
    }
  }, []);

  // Initialize camera stream with cascading fallback constraints
  const startCamera = useCallback(async () => {
    setError(null);
    stopCamera();

    if (typeof navigator === 'undefined' || !navigator?.mediaDevices?.getUserMedia) {
      setError('Camera API is not supported in this browser. Please use the Upload button.');
      setHasPermission(false);
      return;
    }

    const constraintAttempts: MediaStreamConstraints[] = [
      {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      },
      {
        video: {
          facingMode: { ideal: facingMode },
        },
        audio: false,
      },
      {
        video: true,
        audio: false,
      },
      {
        video: true,
      },
    ];

    let stream: MediaStream | null = null;
    let lastError: any = null;

    for (const constraints of constraintAttempts) {
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        if (stream) break;
      } catch (err: any) {
        lastError = err;
      }
    }

    if (!stream) {
      console.warn('[useVideoRecorder] Camera access failed across all constraints:', lastError);
      setHasPermission(false);
      const msg =
        lastError?.name === 'NotAllowedError' || lastError?.name === 'PermissionDeniedError'
          ? 'Camera permission was denied. Please allow camera permissions in browser settings or use the Upload button.'
          : lastError?.name === 'NotFoundError' || lastError?.name === 'DevicesNotFoundError'
          ? 'No camera found on this device. Please use the Upload button.'
          : 'Could not access camera. Please check camera permissions or use the Upload button.';
      setError(msg);
      setIsCameraActive(false);
      return;
    }

    mediaStreamRef.current = stream;
    setHasPermission(true);
    setIsCameraActive(true);

    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.muted = true;
      videoRef.current
        .play()
        .catch((e) => console.warn('[useVideoRecorder] Video element play error:', e));
    }
  }, [facingMode, stopCamera]);

  // Keep videoRef synchronized whenever stream or isCameraActive changes
  useEffect(() => {
    if (isCameraActive && mediaStreamRef.current && videoRef.current) {
      if (videoRef.current.srcObject !== mediaStreamRef.current) {
        videoRef.current.srcObject = mediaStreamRef.current;
        videoRef.current.muted = true;
        videoRef.current.play().catch((e) => console.warn('[useVideoRecorder] Sync play error:', e));
      }
    }
  }, [isCameraActive, facingMode]);

  // Switch camera front/back
  const switchCamera = useCallback(() => {
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'));
  }, []);

  // Re-start camera when facingMode changes if camera is active
  useEffect(() => {
    if (isCameraActive) {
      startCamera();
    }
  }, [facingMode]);

  // Start recording video chunks
  const startRecording = useCallback(async () => {
    if (!mediaStreamRef.current) {
      await startCamera();
      if (!mediaStreamRef.current) return;
    }

    chunksRef.current = [];
    try {
      let options: MediaRecorderOptions = {};
      const preferredMimeTypes = [
        'video/webm;codecs=vp9',
        'video/webm;codecs=vp8',
        'video/webm',
        'video/mp4;codecs=avc1',
        'video/mp4',
      ];

      if (typeof MediaRecorder !== 'undefined') {
        for (const mime of preferredMimeTypes) {
          if (MediaRecorder.isTypeSupported(mime)) {
            options = { mimeType: mime };
            break;
          }
        }
      }

      const recorder = new MediaRecorder(mediaStreamRef.current, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const finalMime = recorder.mimeType || options.mimeType || 'video/webm';
        const blob = new Blob(chunksRef.current, { type: finalMime });
        const url = URL.createObjectURL(blob);
        setVideoBlob(blob);
        setVideoUrl(url);
        setMediaSource('live_camera');
      };

      recorder.start(500);
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      setError('Recording failed to start: ' + (err?.message || 'Unknown error'));
    }
  }, [startCamera]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Take snapshot photo from live stream
  const takeSnapshot = useCallback((): { blob: Blob; url: string } | null => {
    if (!videoRef.current) return null;
    const video = videoRef.current;
    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    if (facingMode === 'user') {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, width, height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const blob = dataURLtoBlob(dataUrl);

    setSnapshotBlob(blob);
    setSnapshotUrl(dataUrl);
    setMediaSource('live_camera');

    return { blob, url: dataUrl };
  }, [facingMode]);

  // Handle uploaded file (image or video)
  const setUploadedFile = useCallback((file: File) => {
    stopCamera();
    if (videoUrl && videoUrl.startsWith('blob:')) {
      try { URL.revokeObjectURL(videoUrl); } catch (e) {}
    }
    if (snapshotUrl && snapshotUrl.startsWith('blob:')) {
      try { URL.revokeObjectURL(snapshotUrl); } catch (e) {}
    }

    const url = URL.createObjectURL(file);
    if (file.type.startsWith('video/')) {
      setVideoBlob(file);
      setVideoUrl(url);
      setSnapshotBlob(null);
      setSnapshotUrl(null);
    } else {
      setSnapshotBlob(file);
      setSnapshotUrl(url);
      setVideoBlob(null);
      setVideoUrl(null);
    }
    setMediaSource('gallery_unverified');
  }, [stopCamera, videoUrl, snapshotUrl]);

  // Reset captured state without unmounting stream
  const resetRecording = useCallback(() => {
    setVideoBlob(null);
    if (videoUrl && videoUrl.startsWith('blob:')) {
      try { URL.revokeObjectURL(videoUrl); } catch (e) {}
    }
    setVideoUrl(null);
    setSnapshotBlob(null);
    if (snapshotUrl && snapshotUrl.startsWith('blob:')) {
      try { URL.revokeObjectURL(snapshotUrl); } catch (e) {}
    }
    setSnapshotUrl(null);
    setRecordingTime(0);
    setMediaSource(null);
  }, [videoUrl, snapshotUrl]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCamera();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [stopCamera]);

  return {
    isRecording,
    recordingTime,
    videoBlob,
    videoUrl,
    snapshotBlob,
    snapshotUrl,
    isCameraActive,
    hasPermission,
    error,
    facingMode,
    videoRef,
    setVideoRef,
    startCamera,
    stopCamera,
    startRecording,
    stopRecording,
    takeSnapshot,
    switchCamera,
    resetRecording,
    setUploadedFile,
    mediaSource,
  };
}
