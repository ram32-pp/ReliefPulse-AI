'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { HeaderNavbar } from '@/components/navigation/HeaderNavbar';
import {
  Phone,
  ShieldCheck,
  ShieldAlert,
  MapPin,
  Radio,
  Clock,
  AlertTriangle,
  Mic,
  Truck,
  Check,
  Users,
  HeartPulse,
  Quote,
  Play,
  Pause,
  ArrowRight,
  Search,
  Loader2,
} from 'lucide-react';
import { fetchReportStatus } from '@/lib/api';
import { getUserReportCode, saveUserReport } from '@/lib/userReport';

interface StatusData {
  report_id: string;
  display_code: string;
  status: string;
  vulnerability_level?: string;
  relief_status?: string;
  relief_team_name?: string;
  rescue_eta_minutes?: number;
  audio_url?: string;
  location_name?: string;
  voice_transcript?: string;
  acoustic_distress_level?: string;
  parsed_text?: string;
  raw_input?: string;
  ai_extraction?: {
    parsed_text?: string;
    hazard_type?: any;
    headcount?: number;
    people?: {
      headcount?: number;
      vulnerable_groups?: string[];
      trapped_count?: number;
    };
    vulnerable_groups?: string[];
    medical_urgencies?: {
      has_medical_emergency?: boolean;
      urgency_level?: string;
      injuries_reported?: string[];
      immediate_needs?: string[];
      details?: string;
    };
    situation_summary?: string;
    urgency?: string;
    [key: string]: any;
  };
  timeline?: Array<{
    step: string;
    label_ur: string;
    label_en: string;
    completed: boolean;
    at?: string;
  }>;
}

export default function StatusPage() {
  const router = useRouter();
  const rawParams = useParams();
  const code = (rawParams?.code as string) || '';
  const { t, isRTL } = useTranslation();

  const [isMounted, setIsMounted] = useState(false);
  const [statusData, setStatusData] = useState<StatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isNotFound, setIsNotFound] = useState(false);
  const [myStoredCode, setMyStoredCode] = useState<string | null>(null);
  const [trackSearchInput, setTrackSearchInput] = useState('');

  // Audio Playback state for caller voice note
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setIsMounted(true);
    setMyStoredCode(getUserReportCode());
  }, []);

  const toggleAudio = () => {
    if (!audioElementRef.current) return;
    if (isAudioPlaying) {
      audioElementRef.current.pause();
      setIsAudioPlaying(false);
    } else {
      audioElementRef.current
        .play()
        .then(() => setIsAudioPlaying(true))
        .catch((e) => console.warn('Audio play failed:', e));
    }
  };

  const loadStatus = async () => {
    const rawCode = (code || '').trim();
    let targetCode = rawCode;

    // If code is generic ('latest', 'rp-latest', 'rp-queued', 'rp-new'), prefer user's stored report if exists
    if (!targetCode || ['latest', 'rp-latest', 'rp-queued', 'rp-new'].includes(targetCode.toLowerCase())) {
      const stored = getUserReportCode();
      if (stored && !['latest', 'rp-latest', 'rp-queued', 'rp-new'].includes(stored.toLowerCase())) {
        targetCode = stored;
      } else {
        targetCode = 'latest';
      }
    }

    try {
      const data = await fetchReportStatus(targetCode);
      if (!data || !data.report_id) {
        // If specific code failed, try latest report fallback
        if (targetCode !== 'latest') {
          const fallbackData = await fetchReportStatus('latest').catch(() => null);
          if (fallbackData?.report_id) {
            setStatusData(fallbackData);
            setIsNotFound(false);
            if (fallbackData.display_code) {
              saveUserReport(fallbackData.display_code, fallbackData.report_id);
              setMyStoredCode(fallbackData.display_code);
            }
            return;
          }
        }
        setIsNotFound(true);
        setStatusData(null);
      } else {
        setStatusData(data);
        setIsNotFound(false);
        // Persist the active display code in user storage
        if (data.display_code) {
          saveUserReport(data.display_code, data.report_id);
          setMyStoredCode(data.display_code);
        }
      }
    } catch (err) {
      console.warn('[Status] Live fetch failed or report not found:', err);
      // Try fallback to latest if code was not found
      try {
        const fallbackData = await fetchReportStatus('latest');
        if (fallbackData?.report_id) {
          setStatusData(fallbackData);
          setIsNotFound(false);
          if (fallbackData.display_code) {
            saveUserReport(fallbackData.display_code, fallbackData.report_id);
            setMyStoredCode(fallbackData.display_code);
          }
          return;
        }
      } catch {}
      setIsNotFound(true);
      setStatusData(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (code) {
      loadStatus();
    }
    // Poll every 5s if in progress, otherwise 12s
    const pollInterval = statusData?.status === 'pending_audit' ? 5000 : 12000;
    const interval = setInterval(() => {
      if (code && !isNotFound) {
        loadStatus();
      }
    }, pollInterval);
    return () => clearInterval(interval);
  }, [code, statusData?.status, isNotFound]);

  const handleSearchOther = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = trackSearchInput.trim().replace(/^#/, '');
    if (clean) {
      router.push(`/status/${clean.toUpperCase()}`);
    }
  };

  const vulnerability = (statusData?.vulnerability_level || 'high').toLowerCase();
  const reliefStatus = statusData?.relief_status || 'dispatched';

  const getVulnerabilityBadge = (vuln: string) => {
    switch (vuln) {
      case 'critical':
        return (
          <span className="px-3 py-1 rounded-full bg-pulse-red/20 text-pulse-red border border-pulse-red/40 font-mono font-black text-xs uppercase tracking-wider flex items-center gap-1.5 shadow-[0_0_12px_rgba(255,42,76,0.35)] animate-pulse">
            <ShieldAlert size={14} /> CRITICAL EMERGENCY
          </span>
        );
      case 'high':
        return (
          <span className="px-3 py-1 rounded-full bg-amber-alert/20 text-amber-alert border border-amber-alert/40 font-mono font-black text-xs uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle size={14} /> HIGH PRIORITY
          </span>
        );
      case 'elevated':
      case 'medium':
        return (
          <span className="px-3 py-1 rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/40 font-mono font-black text-xs uppercase tracking-wider">
            ELEVATED PRIORITY
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full bg-sky-blue/20 text-sky-blue border border-sky-blue/40 font-mono font-black text-xs uppercase tracking-wider">
            ROUTINE / MONITORED
          </span>
        );
    }
  };

  const stages = [
    {
      id: 'received',
      label: 'SOS Broadcast Received',
      sub: 'Emergency dispatch transmission logged',
      done: true,
    },
    {
      id: 'verified',
      label: 'Emergency Verified & Priority Assigned',
      sub: 'Voice details, location & triage confirmed',
      done: ['verified', 'dispatched', 'en_route', 'delivered', 'resolved'].includes(reliefStatus),
    },
    {
      id: 'dispatched',
      label: 'Rescue Team Dispatched',
      sub: `${statusData?.relief_team_name || 'Rescue 1122 Unit'} assigned`,
      done: ['dispatched', 'en_route', 'delivered', 'resolved'].includes(reliefStatus),
    },
    {
      id: 'delivered',
      label: 'Relief Delivered & Safe',
      sub: 'On-site assistance & evacuation complete',
      done: ['delivered', 'resolved'].includes(reliefStatus),
    },
  ];

  if (!isMounted || isLoading) {
    return (
      <div
        suppressHydrationWarning
        className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center text-slate-400 text-xs gap-3 font-sans"
      >
        <Loader2 className="animate-spin text-sky-blue" size={28} />
        <span>Loading Live Emergency Status...</span>
      </div>
    );
  }

  // Not Found State
  if (isNotFound || !statusData) {
    return (
      <div
        suppressHydrationWarning
        className="min-h-screen flex flex-col items-center relative overflow-x-hidden pb-20 font-sans"
      >
        {/* Dynamic Background */}
        <div
          suppressHydrationWarning
          className="fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,42,76,0.14),transparent_40%),radial-gradient(circle_at_bottom_right,_rgba(0,176,255,0.12),transparent_40%)] -z-20 pointer-events-none"
        />

        {/* Header */}
        <div
          suppressHydrationWarning
          className="w-full max-w-5xl mx-auto px-3 sm:px-6 pt-2 sm:pt-4 mb-6"
        >
          <HeaderNavbar />
        </div>

        <main className="w-full max-w-lg mx-auto px-4 flex flex-col items-center text-center my-auto pt-6">
          <div className="w-full glass rounded-3xl p-6 sm:p-8 border border-white/15 shadow-2xl">
            <div className="w-16 h-16 rounded-2xl bg-pulse-red/15 text-pulse-red border border-pulse-red/30 flex items-center justify-center mx-auto mb-4">
              <ShieldAlert size={32} />
            </div>

            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest block mb-1">
              Incident Not Found
            </span>
            <h1 className="text-xl sm:text-2xl font-black text-warm-white font-mono mb-3">
              #{code ? code.toUpperCase() : 'UNKNOWN'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-6">
              We could not find an active emergency report for this code. If you are in immediate danger or need rescue, broadcast an SOS request right now.
            </p>

            {/* If user has their own active report in storage that differs */}
            {myStoredCode && myStoredCode.toUpperCase() !== code.toUpperCase() && (
              <div className="mb-6 p-4 rounded-2xl bg-sky-blue/15 border border-sky-blue/30 text-left flex items-center justify-between gap-3 shadow-md">
                <div>
                  <span className="text-[10px] font-mono uppercase text-sky-300 font-bold block">
                    Your Active Request
                  </span>
                  <span className="text-sm font-black text-warm-white font-mono">
                    #{myStoredCode}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => router.push(`/status/${myStoredCode}`)}
                  className="px-3.5 py-2 rounded-xl bg-sky-blue text-slate-950 font-bold text-xs hover:bg-sky-400 transition-all cursor-pointer shadow active:scale-95"
                >
                  Track My Report &rarr;
                </button>
              </div>
            )}

            <button
              type="button"
              onClick={() => router.push('/sos')}
              className="w-full bg-gradient-to-r from-pulse-red to-rose-600 hover:from-red-600 hover:to-rose-700 text-white font-bold text-sm sm:text-base py-4 rounded-2xl shadow-[0_10px_30px_rgba(255,42,76,0.4)] active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer mb-6"
            >
              <Radio size={18} className="animate-pulse" />
              <span>Broadcast Emergency SOS Now</span>
            </button>

            {/* Track Another Code Search */}
            <div className="pt-5 border-t border-white/10 text-left">
              <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block mb-2">
                Track Another Code
              </span>
              <form onSubmit={handleSearchOther} className="flex gap-2">
                <input
                  type="text"
                  value={trackSearchInput}
                  onChange={(e) => setTrackSearchInput(e.target.value)}
                  placeholder="e.g. RP-2847"
                  className="flex-grow bg-slate-900/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-xs text-warm-white font-mono uppercase focus:outline-none focus:border-sky-blue"
                />
                <button
                  type="submit"
                  disabled={!trackSearchInput.trim()}
                  className="px-4 py-2.5 rounded-xl bg-sky-blue text-slate-950 font-bold text-xs disabled:opacity-50 transition-all cursor-pointer shrink-0"
                >
                  <Search size={14} />
                </button>
              </form>
            </div>
          </div>

          {/* Quick Helpline Hotline */}
          <div className="mt-5 w-full glass rounded-2xl p-4 border border-amber-alert/30 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-warm-white font-semibold">
              <Phone size={16} className="text-sky-blue" />
              <span>Emergency Services Hotline</span>
            </div>
            <a
              href="tel:1122"
              className="px-3 py-1.5 rounded-xl bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue font-bold text-xs border border-sky-blue/40 flex items-center gap-1.5 transition-all cursor-pointer"
            >
              Call 1122
            </a>
          </div>
        </main>
      </div>
    );
  }

  // Active Report Details View
  return (
    <div
      suppressHydrationWarning
      className="min-h-screen flex flex-col items-center relative overflow-x-hidden pb-20 font-sans"
    >
      {/* Background Ambient Lights */}
      <div
        suppressHydrationWarning
        className="fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,230,118,0.14),transparent_45%),radial-gradient(circle_at_bottom_right,_rgba(0,176,255,0.12),transparent_40%)] -z-20 pointer-events-none"
      />

      {/* Unified Global Header Navbar */}
      <div
        suppressHydrationWarning
        className="w-full max-w-5xl mx-auto px-3 sm:px-6 pt-2 sm:pt-4 mb-4"
      >
        <HeaderNavbar />
      </div>

      {/* Main Status Container */}
      <main className="w-full max-w-2xl mx-auto px-3 sm:px-4 flex flex-col">
        {/* Tracking Live Beacon */}
        <div className="flex items-center justify-between px-2 mb-3">
          <div className="flex items-center gap-2">
            <Radio size={15} className="text-relief-green animate-pulse" />
            <span className="text-xs font-mono font-bold text-relief-green tracking-widest uppercase">
              LIVE EMERGENCY STATUS
            </span>
          </div>

          <span className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-relief-green animate-ping" />
            SIGNAL ACTIVE
          </span>
        </div>

        {/* Top Header Card */}
        <div className="glass rounded-3xl p-5 sm:p-7 shadow-2xl mb-5 border border-white/15">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5 border-b border-white/10 pb-4">
            <div>
              <span className="text-[10px] uppercase tracking-widest text-slate-400 font-mono block">
                YOUR INCIDENT TRACKING CODE
              </span>
              <h1 className="text-2xl sm:text-3xl font-black text-warm-white font-mono tabular-nums flex items-center gap-2 mt-0.5">
                #{statusData.display_code || code}
              </h1>
              {statusData.location_name && (
                <p className="text-xs text-slate-300 flex items-center gap-1.5 mt-1 font-sans">
                  <MapPin size={13} className="text-pulse-red shrink-0" />
                  <span>{statusData.location_name}</span>
                </p>
              )}
            </div>

            <div className="flex flex-col items-end gap-1.5">
              {getVulnerabilityBadge(vulnerability)}
              <span className="text-[10px] text-slate-400 font-mono uppercase">
                STATUS: {statusData.relief_status ? statusData.relief_status.replace(/_/g, ' ') : statusData.status}
              </span>
            </div>
          </div>

          {/* Verification in Progress Alert */}
          {statusData.status === 'pending_audit' && (
            <div className="mb-5 p-4 rounded-2xl bg-amber-alert/10 border border-amber-alert/30 flex items-center gap-3 text-xs text-amber-300">
              <Loader2 className="animate-spin text-amber-alert shrink-0" size={20} />
              <div>
                <span className="font-bold block text-sm">Emergency Broadcast Received</span>
                <span className="text-slate-300 text-xs">
                  Responders are reviewing your location and dispatching emergency relief.
                </span>
              </div>
            </div>
          )}

          {/* Quick ETA & Hotline Bar */}
          <div className="p-4 rounded-2xl bg-slate-950/80 border border-amber-alert/30 mb-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-amber-alert/20 text-amber-alert shrink-0">
                <Clock size={20} />
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                  Estimated Rescue Arrival
                </span>
                <span className="text-lg font-black font-mono tabular-nums text-amber-alert">
                  ~{statusData.rescue_eta_minutes || 20} min
                </span>
                <span className="text-[11px] text-slate-400 block">
                  {statusData.relief_team_name || 'Rescue 1122 Rapid Response Team'}
                </span>
              </div>
            </div>

            <a
              href="tel:1122"
              className="flex items-center gap-2 font-bold text-xs text-sky-blue bg-sky-blue/15 hover:bg-sky-blue/25 px-4 py-2.5 rounded-xl border border-sky-blue/30 transition-all active:scale-95 cursor-pointer shadow-md"
            >
              <Phone size={14} /> Call 1122 (Toll Free)
            </a>
          </div>

          {/* Dedicated Voice Note Audio Playback Player (if caller recorded voice) */}
          {statusData.audio_url && (
            <div className="mb-5 p-4 rounded-2xl bg-slate-950/90 border border-sky-blue/30 shadow-lg">
              <audio
                ref={audioElementRef}
                src={statusData.audio_url}
                onLoadedMetadata={(e) => setAudioDuration(e.currentTarget.duration)}
                onTimeUpdate={(e) => setAudioCurrentTime(e.currentTarget.currentTime)}
                onEnded={() => {
                  setIsAudioPlaying(false);
                  setAudioCurrentTime(0);
                }}
              />
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-xl bg-sky-blue/20 text-sky-blue">
                    <Mic size={18} />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-warm-white uppercase tracking-wider">
                      Your Recorded Voice Note
                    </h4>
                    <span className="text-[10px] font-mono text-slate-400">
                      Dispatched with your SOS report
                    </span>
                  </div>
                </div>

                {statusData.acoustic_distress_level && (
                  <span className="px-2.5 py-1 rounded-full bg-amber-alert/15 text-amber-alert border border-amber-alert/30 text-[10px] font-mono font-bold uppercase">
                    Distress: {statusData.acoustic_distress_level}
                  </span>
                )}
              </div>

              {/* Play / Progress Bar */}
              <div className="flex items-center gap-3 bg-white/5 p-2 rounded-xl border border-white/10">
                <button
                  type="button"
                  onClick={toggleAudio}
                  className="w-10 h-10 rounded-lg bg-sky-blue text-slate-950 flex items-center justify-center font-bold active:scale-95 transition-all cursor-pointer shadow-md shrink-0"
                >
                  {isAudioPlaying ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
                </button>

                <div className="flex-grow">
                  <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-sky-blue to-relief-green rounded-full transition-all duration-100"
                      style={{
                        width: `${audioDuration > 0 ? (audioCurrentTime / audioDuration) * 100 : 0}%`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
                    <span>
                      {Math.floor(audioCurrentTime / 60)}:
                      {Math.floor(audioCurrentTime % 60).toString().padStart(2, '0')}
                    </span>
                    <span>
                      {Math.floor(audioDuration / 60)}:
                      {Math.floor(audioDuration % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* User's Distress Statement & Extracted Attributes */}
          {((statusData.parsed_text || statusData.voice_transcript || statusData.raw_input) || statusData.ai_extraction) && (
            <div className="glass rounded-2xl p-4 sm:p-5 mb-5 border border-white/10">
              {/* Distress Statement (Transcription or Typed Text) */}
              {(statusData.voice_transcript || statusData.parsed_text || statusData.raw_input) && (
                <div className="mb-4 p-3.5 rounded-xl bg-slate-950/80 border border-white/10">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5 text-slate-400 text-xs font-mono uppercase tracking-wider">
                      <Quote size={13} className="text-sky-blue" />
                      <span>{statusData.voice_transcript ? 'Voice SOS Transcription' : 'Report Statement'}</span>
                    </div>
                  </div>
                  <p className="text-xs sm:text-sm text-warm-white font-medium leading-relaxed italic pl-2.5 rtl:pl-0 rtl:pr-2.5 border-l-2 rtl:border-l-0 rtl:border-r-2 border-relief-green">
                    &ldquo;{statusData.voice_transcript || statusData.parsed_text || statusData.raw_input}&rdquo;
                  </p>
                </div>
              )}

              {/* 4 Structured Vital Attributes */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {/* 1. Hazard Type */}
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-start gap-2.5">
                  <div className="p-1.5 rounded-lg bg-rose-500/20 text-rose-400 shrink-0 mt-0.5">
                    <AlertTriangle size={15} />
                  </div>
                  <div className="min-w-0 flex-grow">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                      Hazard
                    </span>
                    <span className="text-xs font-bold text-warm-white capitalize truncate block mt-0.5">
                      {(() => {
                        const hz = statusData.ai_extraction?.hazard_type;
                        if (typeof hz === 'string') return hz.replace(/_/g, ' ');
                        if (Array.isArray(hz)) return hz.map(String).join(', ');
                        return 'Emergency Incident';
                      })()}
                    </span>
                  </div>
                </div>

                {/* 2. Headcount */}
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-start gap-2.5">
                  <div className="p-1.5 rounded-lg bg-sky-blue/20 text-sky-blue shrink-0 mt-0.5">
                    <Users size={15} />
                  </div>
                  <div className="min-w-0 flex-grow">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                      Victims Reported
                    </span>
                    <span className="text-xs font-bold text-warm-white block mt-0.5">
                      {statusData.ai_extraction?.headcount ??
                        statusData.ai_extraction?.people?.headcount ??
                        1}{' '}
                      individuals
                      {statusData.ai_extraction?.people?.trapped_count ? (
                        <span className="ml-1 text-rose-400 text-[11px] font-mono">
                          ({statusData.ai_extraction.people.trapped_count} trapped)
                        </span>
                      ) : null}
                    </span>
                  </div>
                </div>

                {/* 3. Vulnerable Groups */}
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-start gap-2.5">
                  <div className="p-1.5 rounded-lg bg-amber-alert/20 text-amber-alert shrink-0 mt-0.5">
                    <ShieldAlert size={15} />
                  </div>
                  <div className="min-w-0 flex-grow">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                      High-Priority
                    </span>
                    <div className="mt-0.5 flex flex-wrap gap-1">
                      {(() => {
                        const groups =
                          statusData.ai_extraction?.vulnerable_groups ||
                          statusData.ai_extraction?.people?.vulnerable_groups ||
                          [];
                        if (!groups || groups.length === 0) {
                          return <span className="text-xs text-slate-400 italic">None reported</span>;
                        }
                        return groups.map((g: any, i: number) => {
                          const label =
                            typeof g === 'string'
                              ? g.replace(/_/g, ' ')
                              : typeof g === 'object' && g !== null
                              ? (g.type || g.name || 'Vulnerable').replace(/_/g, ' ')
                              : String(g);
                          return (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 rounded bg-amber-alert/15 text-amber-300 text-[10px] font-mono font-bold capitalize"
                            >
                              {label}
                            </span>
                          );
                        });
                      })()}
                    </div>
                  </div>
                </div>

                {/* 4. Medical Needs */}
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-start gap-2.5">
                  <div className="p-1.5 rounded-lg bg-red-500/20 text-pulse-red shrink-0 mt-0.5">
                    <HeartPulse size={15} />
                  </div>
                  <div className="min-w-0 flex-grow">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                      Medical Urgencies
                    </span>
                    <span className="text-xs font-bold text-warm-white block mt-0.5">
                      {statusData.ai_extraction?.medical_urgencies?.details ||
                        (statusData.ai_extraction?.medical_urgencies?.immediate_needs?.join(', ') ?? 'None reported')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Simple 4-Step Relief Progress Timeline */}
          <div className="border-t border-white/10 pt-5">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Truck size={15} className="text-sky-blue" />
              Rescue Progress Milestones
            </h4>

            <div className="space-y-4 relative pl-6 rtl:pl-0 rtl:pr-6 border-l-2 rtl:border-l-0 rtl:border-r-2 border-white/10 ml-2 rtl:ml-0 rtl:mr-2">
              {stages.map((st, idx) => (
                <div key={st.id} className="relative">
                  <div
                    className={`absolute -left-[31px] rtl:-left-auto rtl:-right-[31px] top-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      st.done
                        ? 'bg-relief-green text-slate-950 shadow-[0_0_10px_rgba(0,230,118,0.5)]'
                        : 'bg-slate-800 text-slate-400 border border-white/10'
                    }`}
                  >
                    {st.done ? <Check size={13} /> : idx + 1}
                  </div>
                  <div>
                    <h5
                      className={`text-xs font-bold ${
                        st.done ? 'text-warm-white' : 'text-slate-500'
                      }`}
                    >
                      {st.label}
                    </h5>
                    <p className="text-[11px] text-slate-400 mt-0.5">{st.sub}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Immediate Safety Directives */}
        <div className="glass rounded-2xl p-4 sm:p-5 mb-5 border border-white/10 text-xs text-slate-300">
          <h4 className="font-bold text-warm-white mb-2.5 flex items-center gap-1.5">
            <ShieldCheck size={16} className="text-relief-green" /> Immediate Safety Directives
          </h4>
          <ul className="space-y-2 text-slate-300 list-disc pl-4 rtl:pr-4 rtl:pl-0">
            <li>Move to higher ground or upper floor; keep clear of electrical wires and submerged fixtures.</li>
            <li>Keep this page open on your phone; your coordinates and status remain live.</li>
            <li>Conserve phone battery: dim screen brightness and keep lines open for responder calls.</li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={() => router.push('/sos')}
            className="flex-1 bg-white/5 hover:bg-white/10 border border-pulse-red/40 text-pulse-red font-bold text-xs sm:text-sm py-3.5 rounded-xl active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md"
          >
            <Radio size={16} />
            <span>Broadcast Additional SOS</span>
          </button>
          <button
            type="button"
            onClick={() => router.push('/')}
            className="flex-1 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-bold text-xs sm:text-sm py-3.5 rounded-xl active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Back to Home</span>
          </button>
        </div>
      </main>
    </div>
  );
}
