'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import nextDynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { HeaderNavbar } from '@/components/navigation/HeaderNavbar';
import { VoiceRecorder } from '@/components/ui/VoiceRecorder';
import { QuickButtons } from '@/components/ui/QuickButtons';
import {
  ArrowLeft,
  ArrowRight,
  MapPin,
  Mic,
  FileText,
  ShieldAlert,
  Send,
  CheckCircle2,
  AlertTriangle,
  Compass,
  Sparkles,
  Loader2,
  Check,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  Crosshair,
} from 'lucide-react';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { useOfflineQueue } from '@/hooks/useOfflineQueue';
import { useGeolocation } from '@/hooks/useGeolocation';
import { uploadReport } from '@/lib/api';
import { API_BASE_URL } from '@/lib/constants';
import { saveUserReport } from '@/lib/userReport';

const MapLocationPicker = nextDynamic(
  () => import('@/components/maps/MapLocationPicker').then((mod) => mod.MapLocationPicker),
  {
    ssr: false,
    loading: () => (
      <div className="h-[320px] w-full bg-slate-900/80 animate-pulse rounded-2xl border border-white/10 flex flex-col items-center justify-center text-slate-400 text-xs gap-2">
        <Loader2 className="animate-spin text-sky-blue" size={24} />
        <span>Loading Interactive Emergency Map...</span>
      </div>
    ),
  }
);

function SOSWizardContent() {
  const router = useRouter();
  const { t, isRTL } = useTranslation();
  const isOnline = useOnlineStatus();
  const { enqueueRequest } = useOfflineQueue();
  const { coords } = useGeolocation();

  // 3-Step Rapid Dispatch Wizard State
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);

  // Step 1: Geolocation & Auto-Detect GPS Toggle
  const [location, setLocation] = useState({ lat: 24.8607, lng: 67.0011 });
  const [addressText, setAddressText] = useState('Acquiring high-accuracy GPS coordinates...');
  const [isLocationConfirmed, setIsLocationConfirmed] = useState(false);
  const [autoDetectGps, setAutoDetectGps] = useState(true);

  // Step 2: Voice Note + Text + Hazard Badges
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [selectedHazards, setSelectedHazards] = useState<string[]>([]);

  // Audio Playback state for Step 3 Review
  const [isReviewPlaying, setIsReviewPlaying] = useState(false);
  const reviewAudioRef = useRef<HTMLAudioElement | null>(null);

  // Step 3: Fast-Path Submission (<300ms)
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  // Auto-fill coordinates when GPS is acquired
  useEffect(() => {
    if (coords && !isLocationConfirmed && autoDetectGps) {
      setLocation({ lat: coords.latitude, lng: coords.longitude });
      setAddressText(`${coords.latitude.toFixed(5)}° N, ${coords.longitude.toFixed(5)}° E (Live GPS)`);
    }
  }, [coords, isLocationConfirmed, autoDetectGps]);

  // Manage review audio preview URL
  useEffect(() => {
    if (audioBlob) {
      const url = URL.createObjectURL(audioBlob);
      setAudioPreviewUrl(url);
      return () => {
        URL.revokeObjectURL(url);
        setAudioPreviewUrl(null);
      };
    } else {
      setAudioPreviewUrl(null);
    }
  }, [audioBlob]);

  const handleLocationSelect = (lat: number, lng: number, address?: string) => {
    setLocation({ lat, lng });
    if (address) setAddressText(address);
  };

  const handleHazardToggle = (hazardType: string) => {
    if (selectedHazards.includes(hazardType)) {
      setSelectedHazards(selectedHazards.filter((h) => h !== hazardType));
    } else {
      setSelectedHazards([...selectedHazards, hazardType]);
    }
  };

  const toggleReviewAudio = () => {
    if (!reviewAudioRef.current || !audioPreviewUrl) return;
    if (isReviewPlaying) {
      reviewAudioRef.current.pause();
      setIsReviewPlaying(false);
    } else {
      reviewAudioRef.current
        .play()
        .then(() => setIsReviewPlaying(true))
        .catch((err) => console.warn('Audio review play error:', err));
    }
  };

  const handleFinalSubmit = async () => {
    setIsSubmitting(true);
    setSubmissionError(null);

    // 3-Minute Device Rate Limit Prevention
    const lastSosTs = typeof window !== 'undefined' ? localStorage.getItem('rp_last_sos_ts') : null;
    if (lastSosTs) {
      const elapsed = Date.now() - parseInt(lastSosTs, 10);
      if (elapsed < 180000) {
        const remainingSecs = Math.ceil((180000 - elapsed) / 1000);
        setSubmissionError(
          `SOS Broadcast Active: Your emergency broadcast was recently received. Emergency services are handling your signal. To preserve network bandwidth, submissions are rate-limited to 1 per 3 minutes (cooldown remaining: ${remainingSecs}s).`
        );
        setIsSubmitting(false);
        return;
      }
    }

    try {
      // Build ultra-lean low-bandwidth multipart payload
      const formData = new FormData();
      formData.append('input_type', audioBlob ? 'voice' : 'text');
      if (text) formData.append('text_input', text);
      formData.append('address_text', addressText);
      formData.append('latitude', location.lat.toString());
      formData.append('longitude', location.lng.toString());
      formData.append(
        'hazard_types',
        JSON.stringify(selectedHazards.length > 0 ? selectedHazards : ['general_sos'])
      );

      if (audioBlob) {
        formData.append('audio_file', audioBlob, 'emergency_voice_note.webm');
      }

      if (isOnline) {
        try {
          const res = await uploadReport(formData);
          const trackCode = res?.display_code || (res?.report_id ? `RP-${res.report_id.slice(0, 4).toUpperCase()}` : 'RP-LATEST');
          saveUserReport(trackCode, res?.report_id);
          localStorage.setItem('rp_last_sos_ts', Date.now().toString());
          router.push(`/status/${trackCode}`);
        } catch (err: any) {
          console.warn('[SOS] Online upload failed, falling back to offline queue:', err);
          const offlineCode = `RP-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
          saveUserReport(offlineCode);
          await enqueueRequest(`${API_BASE_URL}/reports`, 'POST', {
            latitude: location.lat,
            longitude: location.lng,
            address_text: addressText,
            text_input: text || '',
            input_type: audioBlob ? 'voice' : 'text',
            hazards: selectedHazards,
            media_source: 'voice_direct',
          });
          localStorage.setItem('rp_last_sos_ts', Date.now().toString());
          router.push(`/status/${offlineCode}`);
        }
      } else {
        const offlineCode = `RP-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
        saveUserReport(offlineCode);
        await enqueueRequest(`${API_BASE_URL}/reports`, 'POST', {
          latitude: location.lat,
          longitude: location.lng,
          address_text: addressText,
          text_input: text || '',
          input_type: audioBlob ? 'voice' : 'text',
          hazards: selectedHazards,
          media_source: 'voice_direct',
        });
        localStorage.setItem('rp_last_sos_ts', Date.now().toString());
        router.push(`/status/${offlineCode}`);
      }
    } catch (err: any) {
      setSubmissionError(err?.message || 'Failed to broadcast SOS. Please contact emergency services immediately.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const ArrowIcon = isRTL ? ArrowLeft : ArrowRight;
  const BackIcon = isRTL ? ArrowRight : ArrowLeft;

  if (!isMounted) {
    return (
      <div
        suppressHydrationWarning
        className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center text-slate-400 text-xs gap-3 font-sans"
      >
        <Loader2 className="animate-spin text-sky-blue" size={24} />
        <span>Initializing Emergency Dispatch Wizard...</span>
      </div>
    );
  }

  return (
    <div
      suppressHydrationWarning
      className="min-h-screen flex flex-col items-center relative overflow-x-hidden pb-20 font-sans"
    >
      {/* Dynamic Ambient Background Lights */}
      <div
        suppressHydrationWarning
        className="fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,42,76,0.22),transparent_40%),radial-gradient(circle_at_bottom_left,_rgba(0,176,255,0.18),transparent_40%)] -z-20 pointer-events-none"
      />

      {/* Global Header Navbar */}
      <div
        suppressHydrationWarning
        className="w-full max-w-5xl mx-auto px-3 sm:px-6 pt-2 sm:pt-4 mb-4"
      >
        <HeaderNavbar />
      </div>

      {/* Main Guided 3-Step Wizard Container */}
      <main className="w-full max-w-2xl mx-auto px-3 sm:px-4 flex flex-col">
        {/* Step Progress Tracker Bar (3-Step Pipeline) */}
        <div className="glass rounded-2xl p-3 sm:p-4 mb-5 border border-white/15 shadow-xl">
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            {/* Step 1: Location */}
            <button
              onClick={() => setCurrentStep(1)}
              className={`flex flex-col items-center gap-1 transition-all cursor-pointer ${
                currentStep === 1
                  ? 'text-sky-blue font-bold'
                  : currentStep > 1
                  ? 'text-relief-green'
                  : 'text-slate-500'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-all ${
                  currentStep === 1
                    ? 'bg-sky-blue text-slate-950 shadow-[0_0_15px_rgba(0,176,255,0.5)]'
                    : currentStep > 1
                    ? 'bg-relief-green text-slate-950'
                    : 'bg-white/10 text-slate-400'
                }`}
              >
                {currentStep > 1 ? <Check size={16} /> : '1'}
              </div>
              <span className="text-[11px] sm:text-xs font-semibold">1. Incident Location</span>
            </button>

            {/* Step 2: Voice & Situation */}
            <button
              onClick={() => isLocationConfirmed && setCurrentStep(2)}
              disabled={!isLocationConfirmed}
              className={`flex flex-col items-center gap-1 transition-all ${
                currentStep === 2
                  ? 'text-amber-alert font-bold'
                  : currentStep > 2
                  ? 'text-relief-green'
                  : 'text-slate-500'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-all ${
                  currentStep === 2
                    ? 'bg-amber-alert text-slate-950 shadow-[0_0_15px_rgba(255,170,0,0.5)]'
                    : currentStep > 2
                    ? 'bg-relief-green text-slate-950'
                    : 'bg-white/10 text-slate-400'
                }`}
              >
                {currentStep > 2 ? <Check size={16} /> : '2'}
              </div>
              <span className="text-[11px] sm:text-xs font-semibold">2. Voice SOS & Hazards</span>
            </button>

            {/* Step 3: Review & Dispatch */}
            <button
              onClick={() => isLocationConfirmed && setCurrentStep(3)}
              disabled={!isLocationConfirmed}
              className={`flex flex-col items-center gap-1 transition-all ${
                currentStep === 3 ? 'text-pulse-red font-bold' : 'text-slate-500'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-all ${
                  currentStep === 3
                    ? 'bg-pulse-red text-white shadow-[0_0_20px_rgba(255,42,76,0.6)] animate-pulse'
                    : 'bg-white/10 text-slate-400'
                }`}
              >
                3
              </div>
              <span className="text-[11px] sm:text-xs font-semibold">3. Review & Broadcast</span>
            </button>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* STEP 1: RESCUE LOCATION CONFIRMATION                                      */}
        {/* ========================================================================= */}
        {currentStep === 1 && (
          <div className="flex flex-col space-y-4">
            <div className="glass rounded-3xl p-5 border border-white/15 shadow-2xl">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2.5 rounded-2xl bg-sky-blue/20 text-sky-blue border border-sky-blue/30">
                  <MapPin size={22} />
                </div>
                <div>
                  <h2 className="text-lg sm:text-xl font-black text-warm-white">
                    Confirm Exact Rescue Location
                  </h2>
                  <p className="text-xs text-slate-300">
                    Live GPS coordinates pin emergency teams directly to your pinpoint spot.
                  </p>
                </div>
              </div>

              {/* Auto-Detect GPS Toggle Bar */}
              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950/80 border border-white/10 mt-3 mb-2">
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-xl transition-colors ${autoDetectGps ? 'bg-relief-green/20 text-relief-green' : 'bg-white/10 text-slate-400'}`}>
                    <Crosshair size={18} className={autoDetectGps ? 'animate-pulse' : ''} />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-warm-white block">Auto-Detect GPS</span>
                    <span className="text-[10px] text-slate-400 block">
                      {autoDetectGps ? 'High-accuracy satellite coordinate lock active' : 'Manual pin adjustment enabled'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const nextState = !autoDetectGps;
                    setAutoDetectGps(nextState);
                    if (nextState && coords) {
                      setLocation({ lat: coords.latitude, lng: coords.longitude });
                      setAddressText(`${coords.latitude.toFixed(5)}° N, ${coords.longitude.toFixed(5)}° E (GPS Verified)`);
                    }
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
                    autoDetectGps
                      ? 'bg-relief-green text-white shadow-md shadow-relief-green/30'
                      : 'bg-white/10 hover:bg-white/20 text-slate-300'
                  }`}
                >
                  {autoDetectGps ? 'ON' : 'OFF'}
                </button>
              </div>

              {/* Interactive OpenStreetMap Pin Picker */}
              <div className="mt-2 mb-3">
                <MapLocationPicker
                  initialCenter={location}
                  onLocationSelect={handleLocationSelect}
                  height="340px"
                />
              </div>

              {/* Detected Address Details Bar */}
              <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-white/10 flex items-start gap-3">
                <Compass size={18} className="text-sky-blue shrink-0 mt-0.5" />
                <div className="flex-grow">
                  <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400 block">
                    Target Geolocation
                  </span>
                  <p className="text-xs sm:text-sm font-semibold text-warm-white mt-0.5">
                    {addressText}
                  </p>
                  <span className="text-[11px] font-mono text-sky-blue mt-1 inline-block">
                    Coordinates: {location.lat.toFixed(5)}° N, {location.lng.toFixed(5)}° E
                  </span>
                </div>
              </div>

              {/* Confirm & Advance Button */}
              <button
                type="button"
                onClick={() => {
                  setIsLocationConfirmed(true);
                  setCurrentStep(2);
                }}
                className="w-full mt-4 bg-gradient-to-r from-sky-blue via-cyan-500 to-emerald-400 hover:from-sky-400 hover:to-emerald-300 text-slate-950 font-black text-sm sm:text-base py-4 rounded-2xl shadow-[0_10px_30px_rgba(0,176,255,0.35)] transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95"
              >
                <CheckCircle2 size={20} />
                <span>Confirm Rescue Location &amp; Proceed</span>
                <ArrowIcon size={18} />
              </button>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 2: VOICE NOTE + TEXT + HAZARD BADGES                                 */}
        {/* ========================================================================= */}
        {currentStep === 2 && (
          <div className="flex flex-col space-y-4">
            {/* Confirmed Location Mini Header */}
            <div className="glass rounded-2xl px-4 py-2.5 border border-sky-blue/30 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 truncate">
                <MapPin size={15} className="text-sky-blue shrink-0" />
                <span className="text-slate-300 truncate font-medium">{addressText}</span>
              </div>
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="text-sky-blue hover:underline font-bold text-xs shrink-0 cursor-pointer ml-2"
              >
                Edit Location
              </button>
            </div>

            {/* Voice Recording Card */}
            <div className="glass rounded-3xl p-5 border border-white/15 shadow-2xl">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2.5 rounded-2xl bg-amber-alert/20 text-amber-alert border border-amber-alert/30">
                  <Mic size={22} />
                </div>
                <div>
                  <h2 className="text-lg sm:text-xl font-black text-warm-white">
                    Emergency Voice SOS Note
                  </h2>
                  <p className="text-xs text-slate-300">
                    Record voice note (60s max). AI acoustic emotion and keyword analysis runs automatically.
                  </p>
                </div>
              </div>

              {/* Voice Recorder Component with 60s countdown, waveform, and instant audio playback */}
              <div className="mt-3">
                <VoiceRecorder onRecordingComplete={(blob) => setAudioBlob(blob)} />
              </div>

              {/* Fallback / Simultaneous Text Note Area */}
              <div className="mt-5">
                <label className="text-xs font-bold text-slate-300 mb-1.5 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <FileText size={15} className="text-sky-blue" />
                    Additional Situation Note (Optional or Text SOS)
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">Any Language</span>
                </label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="e.g. 5 family members trapped on roof, water rising rapidly. Elderly diabetic patient needs urgent evacuation..."
                  className="w-full bg-slate-950/80 border border-white/15 text-warm-white placeholder:text-slate-500 rounded-2xl p-4 min-h-[100px] text-xs sm:text-sm focus:ring-1 focus:ring-sky-blue focus:border-sky-blue outline-none backdrop-blur-xl transition-all"
                />
              </div>

              {/* 5 Quick Emergency Hazard Badges */}
              <div className="mt-4">
                <QuickButtons onSelect={handleHazardToggle} selectedTypes={selectedHazards} />
              </div>

              {/* Navigation Controls */}
              <div className="flex items-center gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="px-5 py-3.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-bold border border-white/10 flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <BackIcon size={16} />
                  <span>Back</span>
                </button>

                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="flex-grow bg-gradient-to-r from-amber-alert via-orange-500 to-rose-500 hover:from-amber-500 hover:to-rose-600 text-slate-950 font-black text-sm py-4 rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95"
                >
                  <span>Review &amp; Broadcast SOS</span>
                  <ArrowIcon size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 3: REVIEW & BROADCAST SOS DISPATCH                                   */}
        {/* ========================================================================= */}
        {currentStep === 3 && (
          <div className="flex flex-col space-y-4">
            <div className="glass rounded-3xl p-5 sm:p-6 border border-pulse-red/40 shadow-[0_20px_60px_rgba(255,42,76,0.3)]">
              <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-pulse-red text-white shadow-lg animate-pulse">
                    <ShieldAlert size={24} />
                  </div>
                  <div>
                    <h2 className="text-xl sm:text-2xl font-black text-warm-white">
                      Review &amp; Broadcast SOS
                    </h2>
                    <p className="text-xs text-slate-300">
                      High-priority fast path: immediate dispatch alert &lt;300ms.
                    </p>
                  </div>
                </div>

                <span className="px-3 py-1 rounded-full bg-pulse-red/20 text-pulse-red border border-pulse-red/30 text-[10px] font-mono font-bold uppercase tracking-wider">
                  RAPID DISPATCH
                </span>
              </div>

              {/* Review Item 1: Confirmed Location */}
              <div className="p-4 rounded-2xl bg-slate-950/80 border border-white/10 mb-3 flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <MapPin size={20} className="text-pulse-red shrink-0 mt-0.5" />
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400 block">
                      Confirmed Rescue Location
                    </span>
                    <p className="text-xs sm:text-sm font-bold text-warm-white mt-0.5">
                      {addressText}
                    </p>
                    <span className="text-[11px] font-mono text-sky-blue">
                      GPS: {location.lat.toFixed(5)}, {location.lng.toFixed(5)}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="text-xs text-sky-blue hover:underline font-bold shrink-0 cursor-pointer"
                >
                  Edit
                </button>
              </div>

              {/* Review Item 2: Voice SOS Audio Playback & Text */}
              <div className="p-4 rounded-2xl bg-slate-950/80 border border-white/10 mb-3 flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-grow">
                  <Mic size={20} className="text-amber-alert shrink-0 mt-0.5" />
                  <div className="flex-grow">
                    <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400 block">
                      Distress Statement &amp; Audio
                    </span>

                    {/* Recorded Audio Playback Bar */}
                    {audioPreviewUrl ? (
                      <div className="mt-2 p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center gap-3">
                        <audio
                          ref={reviewAudioRef}
                          src={audioPreviewUrl}
                          onEnded={() => setIsReviewPlaying(false)}
                        />
                        <button
                          type="button"
                          onClick={toggleReviewAudio}
                          className="w-8 h-8 rounded-lg bg-sky-blue text-slate-950 flex items-center justify-center font-bold active:scale-95 transition-all"
                        >
                          {isReviewPlaying ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
                        </button>
                        <span className="text-xs text-relief-green font-semibold flex items-center gap-1.5">
                          <CheckCircle2 size={14} /> Voice Note Attached ({((audioBlob?.size || 0) / 1024).toFixed(1)} KB)
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic block mt-1">
                        No audio recorded (Text note / hazard alert will be dispatched)
                      </span>
                    )}

                    {text && (
                      <p className="text-xs text-slate-200 mt-2 italic leading-relaxed bg-white/5 p-2 rounded-lg border border-white/5">
                        &ldquo;{text}&rdquo;
                      </p>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="text-xs text-sky-blue hover:underline font-bold shrink-0 cursor-pointer"
                >
                  Edit
                </button>
              </div>

              {/* Review Item 3: Selected Hazard Badges */}
              {selectedHazards.length > 0 && (
                <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-white/10 mb-4">
                  <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400 block mb-2">
                    Tagged Hazard Badges ({selectedHazards.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedHazards.map((hz) => (
                      <span
                        key={hz}
                        className="px-2.5 py-1 rounded-full bg-amber-alert/15 text-amber-alert border border-amber-alert/30 text-xs font-bold font-mono"
                      >
                        ⚠️ {hz.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Immediate Dispatch Notice */}
              <div className="p-3.5 rounded-2xl bg-sky-blue/10 border border-sky-blue/30 text-xs text-sky-200 mb-6 flex items-start gap-2.5">
                <Sparkles size={18} className="text-sky-blue shrink-0 mt-0.5" />
                <p className="leading-relaxed text-[11px] sm:text-xs">
                  <strong>Instant Dispatch:</strong> Your rescue location and emergency audio will be transmitted directly to Rescue 1122 emergency dispatchers the moment you tap broadcast.
                </p>
              </div>

              {/* Submission Error Banner */}
              {submissionError && (
                <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/50 text-red-200 text-xs mb-4 flex items-center gap-2">
                  <AlertTriangle size={16} className="text-pulse-red shrink-0" />
                  <span>{submissionError}</span>
                </div>
              )}

              {/* Final Emergency Action Button */}
              <button
                type="button"
                onClick={handleFinalSubmit}
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-pulse-red via-red-600 to-rose-700 hover:from-red-600 hover:to-rose-800 text-white font-black text-lg sm:text-xl py-5 rounded-2xl shadow-[0_15px_45px_rgba(255,42,76,0.55)] active:scale-95 transition-all flex items-center justify-center gap-3 border border-red-400/40 uppercase tracking-wider cursor-pointer"
              >
                {isSubmitting ? (
                  <Loader2 size={24} className="animate-spin" />
                ) : (
                  <Send size={24} className="animate-bounce" />
                )}
                <span>
                  {isSubmitting
                    ? 'Broadcasting SOS...'
                    : isOnline
                    ? 'BROADCAST SOS DISPATCH'
                    : 'SAVE DISPATCH OFFLINE'}
                </span>
              </button>

              <div className="flex justify-center mt-3">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <BackIcon size={14} />
                  <span>Back to Voice SOS &amp; Hazards</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function SOSPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-slate-400 text-xs">
          <Loader2 className="animate-spin text-sky-blue mr-2" size={20} />
          <span>Loading Emergency Wizard...</span>
        </div>
      }
    >
      <SOSWizardContent />
    </Suspense>
  );
}
