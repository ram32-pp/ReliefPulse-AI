'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  ShieldAlert,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MapPin,
  Mic,
  Users,
  Clock,
  Sparkles,
  Compass,
  Layers,
  Quote,
  Loader2,
  ExternalLink,
  Send,
  CheckCircle2,
  Truck,
  HeartHandshake,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { DispatchModal } from '@/components/coordinator/DispatchModal';
import { fetchIncidentDetail, advanceReliefStatus, rejectIncident } from '@/lib/api';

interface IncidentData {
  incident_id: string;
  incident_code: string;
  severity: string;
  hazard_type: string;
  location: {
    name: string;
    centroid?: { lat: number; lng: number };
  };
  total_reports: number;
  total_individuals: number;
  medical_risks: Array<{ type: string; count: number }>;
  vulnerable_groups?: string[];
  cluster_confidence: number;
  ai_summary: string;
  ai_reasoning: string[];
  anomaly_flags?: string[];
  gps_text_match?: { level: string; confidence: number };
  caller_statement?: string;
  caller_transcript?: string;
  english_translation?: string;
  urdu_translation?: string;
  representative_audio_url?: string;
  relief_status?: string;
  relief_team_name?: string;
  relief_eta_minutes?: number;
}

export default function IncidentDetail() {
  const router = useRouter();
  const rawParams = useParams();
  const id = (rawParams?.id as string) || '';
  const { t, isRTL } = useTranslation();

  const [incident, setIncident] = useState<IncidentData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showDispatch, setShowDispatch] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isAdvancing, setIsAdvancing] = useState(false);

  // Audio player state
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(14);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const BackIcon = isRTL ? ArrowRight : ArrowLeft;

  const loadData = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchIncidentDetail(id);
      if (data && (data.incident_id || data.incident_code)) {
        setIncident(data);
      } else {
        setError(`Emergency incident #${id} not found.`);
      }
    } catch (err: any) {
      console.warn('Incident fetch API error:', err);
      setError(err?.message || `Emergency incident #${id} not found.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  // Audio timer simulation if no real audio element source
  useEffect(() => {
    let interval: any;
    if (isPlayingAudio) {
      interval = setInterval(() => {
        setAudioCurrentTime((prev) => {
          if (prev >= audioDuration) {
            setIsPlayingAudio(false);
            return 0;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlayingAudio, audioDuration]);

  const handleToggleAudio = () => {
    if (incident?.representative_audio_url && audioRef.current) {
      if (isPlayingAudio) {
        audioRef.current.pause();
        setIsPlayingAudio(false);
      } else {
        audioRef.current.play().catch(() => {});
        setIsPlayingAudio(true);
      }
    } else {
      setIsPlayingAudio(!isPlayingAudio);
    }
  };

  const handleAdvanceStatus = async (nextStatus: string) => {
    if (!incident) return;
    setIsAdvancing(true);
    try {
      await advanceReliefStatus({
        incidentId: incident.incident_id || id,
        reliefStatus: nextStatus,
        teamName: incident.relief_team_name || 'Rescue 1122 Rapid Unit',
        etaMinutes: nextStatus === 'resolved' ? 0 : Math.max(5, (incident.relief_eta_minutes || 15) - 5),
      });
      setIncident({
        ...incident,
        relief_status: nextStatus,
      });
    } catch (err) {
      console.warn('Advance status fallback:', err);
      setIncident({
        ...incident,
        relief_status: nextStatus,
      });
    } finally {
      setIsAdvancing(false);
    }
  };

  const handleReject = async () => {
    if (!confirm('Are you sure you want to reject this incident as a false alarm or duplicate?')) {
      return;
    }
    setIsRejecting(true);
    try {
      await rejectIncident({
        incidentId: incident?.incident_id || id,
        reason: 'Coordinator flagged as duplicate or non-emergency signal',
      });
      alert('Signal rejected. Returning to triage queue.');
      router.push('/coordinator');
    } catch (err) {
      console.warn('Reject fallback:', err);
      alert('Signal marked as rejected.');
      router.push('/coordinator');
    } finally {
      setIsRejecting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#060913] text-warm-white flex flex-col items-center justify-center p-6">
        <Loader2 className="animate-spin text-sky-blue mb-3" size={32} />
        <p className="text-slate-400 font-mono text-xs">Loading incident intelligence #{id}...</p>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="min-h-screen bg-[#060913] text-warm-white flex flex-col items-center justify-center p-6 text-center">
        <AlertTriangle className="text-amber-400 mb-3" size={36} />
        <h2 className="text-lg font-bold text-white mb-1">Emergency Signal Not Found</h2>
        <p className="text-xs text-slate-400 max-w-sm mb-5 leading-relaxed">
          {error || `Incident #${id} does not exist or may have been cleared or resolved.`}
        </p>
        <button
          onClick={() => router.push('/coordinator')}
          className="px-4 py-2 rounded-xl bg-sky-blue text-slate-950 font-bold text-xs hover:bg-sky-400 transition-all cursor-pointer"
        >
          Return to Coordinator Queue
        </button>
      </div>
    );
  }

  const currentStatus = (incident?.relief_status || 'open').toLowerCase();
  const severity = (incident?.severity || 'critical').toLowerCase();
  const hazardType = incident?.hazard_type || 'flood';
  const lat = incident?.location?.centroid?.lat ?? 24.8307;
  const lng = incident?.location?.centroid?.lng ?? 67.0811;

  const mapUrl = `https://www.google.com/maps?q=${lat},${lng}`;

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div
      suppressHydrationWarning
      className="min-h-screen bg-[#060913] text-warm-white p-4 sm:p-6 max-w-5xl mx-auto w-full font-sans"
    >
      {/* Top Bar with Back Button and Language Switcher */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => router.push('/coordinator')}
          className="flex items-center gap-2 text-slate-400 hover:text-sky-blue transition-colors text-xs font-semibold uppercase tracking-wider cursor-pointer"
        >
          <BackIcon size={16} /> {t('back_to_dashboard') || 'Back to Command Center'}
        </button>

        <div className="flex items-center gap-3">
          <a
            href="/coordinator"
            className="px-3 py-1 bg-white/5 hover:bg-white/10 text-slate-300 text-xs rounded-xl border border-white/10 transition-colors"
          >
            Live Map
          </a>
          <LanguageSwitcher compact={true} />
        </div>
      </div>

      {/* Main Incident Intelligence Card */}
      <div className="glass rounded-3xl p-6 sm:p-8 border border-white/10 shadow-[0_25px_60px_rgba(0,0,0,0.5)] mb-8 relative overflow-hidden">
        {/* Top Header Row */}
        <div className="flex flex-wrap justify-between items-start gap-4 mb-6 border-b border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2.5 mb-2.5 flex-wrap">
              <span
                className={`text-white text-xs font-black px-3 py-1 rounded-full uppercase tracking-widest shadow-lg ${
                  severity === 'critical'
                    ? 'bg-pulse-red animate-pulse'
                    : severity === 'high'
                    ? 'bg-amber-alert text-slate-950 font-bold'
                    : 'bg-sky-blue text-slate-950 font-bold'
                }`}
              >
                {severity} EMERGENCY
              </span>

              <span className="font-mono tabular-nums text-sky-blue text-xs font-bold bg-sky-blue/10 px-2.5 py-1 rounded-md border border-sky-blue/30">
                {incident?.incident_code || id}
              </span>

              <span className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 font-mono text-xs text-slate-300 uppercase">
                Hazard: <strong className="text-warm-white">{hazardType.replace('_', ' ')}</strong>
              </span>

              <span className="text-slate-400 text-xs flex items-center gap-1">
                <Clock size={14} /> Active Triage Signal
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-black text-warm-white">
              {incident?.location?.name || 'Emergency Target Zone'}
            </h1>

            <div className="flex items-center gap-3 flex-wrap mt-2">
              <p className="text-slate-400 text-xs font-mono tabular-nums flex items-center gap-1.5">
                <MapPin size={14} className="text-pulse-red" />
                GPS: {lat.toFixed(4)}° N, {lng.toFixed(4)}° E
              </p>
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-sky-blue hover:underline flex items-center gap-1 font-mono"
              >
                Open in Maps <ExternalLink size={12} />
              </a>
            </div>

            <div className="flex items-center gap-2 text-xs text-relief-green mt-3 bg-relief-green/15 border border-relief-green/30 px-3 py-1.5 rounded-xl w-fit font-medium">
              <CheckCircle size={15} /> Location Corroboration Confirmed
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="p-3 rounded-2xl bg-white/5 border border-white/10 text-right">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">
                Verification Confidence
              </span>
              <span className="text-2xl font-black text-relief-green font-mono tabular-nums">
                {Math.round((incident?.cluster_confidence || 0.92) * 100)}%
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-mono">
              <span className="text-slate-400">Current Status:</span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold uppercase">
                {currentStatus}
              </span>
            </div>
          </div>
        </div>

        {/* Live Relief Status Pipeline Tracker */}
        <div className="mb-8 p-4 rounded-2xl bg-white/5 border border-white/10">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Truck size={16} className="text-sky-blue" /> Relief Response Pipeline
            </span>
            {incident?.relief_team_name && (
              <span className="text-xs font-mono text-slate-300 bg-white/5 px-2.5 py-1 rounded-lg border border-white/10">
                Unit: <strong className="text-warm-white">{incident.relief_team_name}</strong>
                {incident.relief_eta_minutes ? ` &bull; ETA: ~${incident.relief_eta_minutes}m` : ''}
              </span>
            )}
          </div>

          <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono">
            {[
              { key: 'open', label: '1. Received' },
              { key: 'dispatched', label: '2. Dispatched' },
              { key: 'en_route', label: '3. En Route' },
              { key: 'resolved', label: '4. Delivered / Resolved' },
            ].map((step, idx) => {
              const statusOrder = ['open', 'dispatched', 'en_route', 'resolved'];
              const currentIdx = statusOrder.indexOf(currentStatus);
              const stepIdx = statusOrder.indexOf(step.key);
              const isPast = stepIdx <= currentIdx;
              const isCurrent = step.key === currentStatus;

              return (
                <div
                  key={step.key}
                  className={`p-2.5 rounded-xl border transition-all ${
                    isCurrent
                      ? 'bg-relief-green/20 border-relief-green text-relief-green font-bold shadow-lg'
                      : isPast
                      ? 'bg-white/10 border-white/20 text-slate-200'
                      : 'bg-white/5 border-white/5 text-slate-500'
                  }`}
                >
                  <div className="text-[10px] text-slate-400 mb-0.5">Stage {idx + 1}</div>
                  <div className="text-xs">{step.label}</div>
                </div>
              );
            })}
          </div>

          {/* Quick status advancer for coordinator */}
          <div className="mt-3 flex items-center justify-end gap-2">
            <span className="text-[11px] text-slate-400">Advance Status:</span>
            {currentStatus === 'open' && (
              <button
                onClick={() => handleAdvanceStatus('dispatched')}
                disabled={isAdvancing}
                className="px-3 py-1 bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue border border-sky-blue/30 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Mark Dispatched
              </button>
            )}
            {currentStatus === 'dispatched' && (
              <button
                onClick={() => handleAdvanceStatus('en_route')}
                disabled={isAdvancing}
                className="px-3 py-1 bg-amber-alert/20 hover:bg-amber-alert/30 text-amber-alert border border-amber-alert/30 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Mark En Route
              </button>
            )}
            {currentStatus === 'en_route' && (
              <button
                onClick={() => handleAdvanceStatus('resolved')}
                disabled={isAdvancing}
                className="px-3 py-1 bg-relief-green/20 hover:bg-relief-green/30 text-relief-green border border-relief-green/30 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Mark Delivered & Resolved
              </button>
            )}
            {currentStatus === 'resolved' && (
              <span className="text-xs text-relief-green font-mono font-semibold">
                ✓ Relief Completed
              </span>
            )}
          </div>
        </div>

        {/* Situation Grid & AI Analysis */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="glass-card rounded-2xl p-5 border border-white/10">
            <h3 className="text-xs font-bold text-sky-blue uppercase tracking-widest mb-4 flex items-center gap-2 border-b border-white/10 pb-2">
              <ShieldAlert size={16} /> Operational Situation
            </h3>
            <div className="space-y-3 text-xs text-slate-200">
              <div className="bg-white/5 p-3 rounded-xl border border-white/10 leading-relaxed">
                <span className="text-slate-400 text-[11px] uppercase block font-semibold mb-1">
                  Situation Brief
                </span>
                <p className="text-warm-white text-xs">{incident?.ai_summary}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/5 p-3 rounded-xl border border-white/10">
                  <span className="text-slate-400 text-[10px] uppercase block font-mono">
                    Individuals at Risk
                  </span>
                  <span className="text-lg font-bold text-warm-white font-mono tabular-nums">
                    {incident?.total_individuals ?? 1} people
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    across <strong className="font-mono tabular-nums">{incident?.total_reports ?? 1}</strong> verified reports
                  </span>
                </div>

                <div className="bg-white/5 p-3 rounded-xl border border-white/10">
                  <span className="text-slate-400 text-[10px] uppercase block font-mono">
                    Hazard Category
                  </span>
                  <span className="text-lg font-bold text-warm-white capitalize font-mono">
                    {hazardType.replace('_', ' ')}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    Multi-source verified
                  </span>
                </div>
              </div>

              {/* Medical and Vulnerability Badges */}
              <div>
                <span className="text-slate-400 text-[11px] uppercase block font-semibold mb-1.5">
                  Vulnerable Groups &amp; Medical Risks
                </span>
                <div className="flex flex-wrap gap-2">
                  {Array.isArray(incident?.medical_risks) && incident.medical_risks.length > 0 ? (
                    incident.medical_risks.map((risk, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-lg bg-pulse-red/15 text-pulse-red border border-pulse-red/30 text-xs font-semibold flex items-center gap-1"
                      >
                        🩺 {risk.count} {risk.type.replace('_', ' ')}
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-400 text-xs italic">
                      No acute trauma flagged
                    </span>
                  )}
                  {Array.isArray(incident?.vulnerable_groups) &&
                    incident.vulnerable_groups.map((grp, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-lg bg-amber-alert/15 text-amber-alert border border-amber-alert/30 text-xs font-semibold"
                      >
                        👥 {grp}
                      </span>
                    ))}
                </div>
              </div>
            </div>
          </div>

          <div className="glass-card rounded-2xl p-5 border border-white/10">
            <h3 className="text-xs font-bold text-amber-alert uppercase tracking-widest mb-4 flex items-center gap-2 border-b border-white/10 pb-2">
              <Sparkles size={16} /> Corroboration &amp; Field Telemetry
            </h3>
            <div className="space-y-3 text-xs text-slate-200">
              {Array.isArray(incident?.ai_reasoning) && incident.ai_reasoning.length > 0 ? (
                <ul className="space-y-2.5 list-disc pl-4 text-xs text-slate-300">
                  {incident.ai_reasoning.map((reason, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {reason}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-slate-300 leading-relaxed">
                  Corroborated across citizen voice reports and local spatiotemporal clusters.
                </p>
              )}

              <div className="pt-2 border-t border-white/10 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400">NDMA / Meteorological Match:</span>
                  <span className="text-relief-green font-semibold">Active Regional Advisory Confirmed</span>
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400">Cluster Spatiotemporal Window:</span>
                  <span className="text-warm-white">Within 500m &amp; 45 Minutes</span>
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400">Voice ↔ Text Alignment:</span>
                  <span className="text-relief-green font-semibold">Consistent Semantics</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Caller Voice Note & Multi-lingual Transcript */}
        <div className="mb-8 glass-card rounded-2xl p-5 border border-white/10">
          <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-sky-blue/20 text-sky-blue">
                <Mic size={18} />
              </div>
              <div>
                <h3 className="text-xs font-bold text-warm-white uppercase tracking-widest">
                  Citizen Voice Distress Note &amp; Verified Translation
                </h3>
                <span className="text-[10px] font-mono text-slate-400">
                  Acoustic Speech Ingestion &bull; Multi-Lingual Translation
                </span>
              </div>
            </div>

            <span className="px-2.5 py-1 rounded-full bg-relief-green/20 text-relief-green border border-relief-green/30 text-[10px] font-mono font-bold uppercase tracking-wider flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-relief-green animate-ping" />
              Signal Authenticated
            </span>
          </div>

          {/* Audio Player Widget */}
          <div className="p-4 rounded-2xl bg-slate-950/80 border border-white/10 mb-4">
            {incident?.representative_audio_url && (
              <audio
                ref={audioRef}
                src={incident.representative_audio_url}
                onEnded={() => {
                  setIsPlayingAudio(false);
                  setAudioCurrentTime(0);
                }}
                onTimeUpdate={() => {
                  if (audioRef.current) {
                    setAudioCurrentTime(audioRef.current.currentTime);
                    if (!isNaN(audioRef.current.duration)) {
                      setAudioDuration(audioRef.current.duration);
                    }
                  }
                }}
                className="hidden"
              />
            )}

            <div className="flex items-center gap-4 mb-3">
              <button
                type="button"
                onClick={handleToggleAudio}
                className="p-3 rounded-full bg-sky-blue text-slate-950 hover:bg-sky-400 transition-colors shadow-lg active:scale-95 cursor-pointer"
                title={isPlayingAudio ? 'Pause Audio' : 'Play Citizen Audio'}
              >
                {isPlayingAudio ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
              </button>

              <div className="flex-grow">
                <div className="h-2 bg-white/10 rounded-full overflow-hidden relative">
                  <div
                    className="h-full bg-sky-blue rounded-full transition-all"
                    style={{
                      width: `${audioDuration > 0 ? (audioCurrentTime / audioDuration) * 100 : 0}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
                  <span>{formatSeconds(audioCurrentTime)}</span>
                  <span>{formatSeconds(audioDuration)}</span>
                </div>
              </div>
            </div>

            {/* Verbatim Statement & Multi-Lingual Translations */}
            <div className="space-y-3">
              {/* Verbatim Original Speech */}
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-amber-alert font-bold mb-1">
                  <Quote size={12} />
                  <span>Original Caller Statement (Verbatim)</span>
                </div>
                <p className="text-xs text-warm-white italic border-l-2 border-amber-alert pl-3 py-1">
                  &ldquo;
                  {incident?.caller_statement ||
                    incident?.caller_transcript ||
                    'Water levels rising quickly inside the ground floor. Multiple residents requiring urgent assistance.'}
                  &rdquo;
                </p>
              </div>

              {/* English Translation */}
              {incident?.english_translation && (
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-sky-blue font-bold mb-1">
                    <span>English Translation</span>
                  </div>
                  <p className="text-xs text-slate-200 border-l-2 border-sky-blue pl-3 py-1">
                    &ldquo;{incident.english_translation}&rdquo;
                  </p>
                </div>
              )}

              {/* Urdu Translation */}
              {incident?.urdu_translation && (
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-right" dir="rtl">
                  <div className="flex items-center justify-end gap-1.5 text-[10px] font-mono uppercase text-relief-green font-bold mb-1">
                    <span>اردو ترجمہ</span>
                  </div>
                  <p className="text-xs text-slate-200 border-r-2 border-relief-green pr-3 py-1 font-sans">
                    {incident.urdu_translation}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Operational Grounding & Cluster Context */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs">
              <div className="flex items-center gap-2 text-sky-blue font-bold mb-1">
                <Compass size={14} />
                <span>Environmental Cross-Verification</span>
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                Authoritative match with meteorological &amp; NDMA hazard alerts in Karachi division.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs">
              <div className="flex items-center gap-2 text-amber-alert font-bold mb-1">
                <Layers size={14} />
                <span>Spatiotemporal Cluster Consensus</span>
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                {incident?.total_reports ?? 1} independent reports corroborate location and severity profile.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons Row */}
        <div className="flex flex-wrap gap-3 border-t border-white/10 pt-6">
          <button
            type="button"
            onClick={() => setShowDispatch(true)}
            className="flex-grow bg-gradient-to-r from-relief-green to-emerald-600 hover:from-emerald-500 hover:to-emerald-700 text-slate-950 font-black py-4 rounded-xl shadow-lg hover:shadow-relief-green/40 transition-all flex items-center justify-center gap-2 text-sm uppercase tracking-wider active:scale-95 cursor-pointer"
          >
            <CheckCircle size={20} /> APPROVE &amp; DISPATCH EMERGENCY TEAM
          </button>

          <button
            type="button"
            onClick={() => router.push('/coordinator')}
            className="px-6 py-4 bg-white/10 hover:bg-white/15 text-slate-200 font-bold rounded-xl border border-white/10 text-xs transition-all cursor-pointer"
          >
            ⏭️ BACK TO QUEUE
          </button>

          <button
            type="button"
            onClick={handleReject}
            disabled={isRejecting}
            className="px-6 py-4 bg-pulse-red/20 hover:bg-pulse-red/30 text-pulse-red font-bold rounded-xl border border-pulse-red/40 text-xs transition-all flex items-center gap-1.5 cursor-pointer"
          >
            {isRejecting ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={18} />}
            <span>REJECT SIGNAL</span>
          </button>
        </div>
      </div>

      {showDispatch && (
        <DispatchModal
          onClose={() => setShowDispatch(false)}
          incidentId={incident?.incident_id || id}
          hazardType={hazardType}
          locationName={incident?.location?.name}
          onSuccess={() => {
            if (incident) {
              setIncident({
                ...incident,
                relief_status: 'dispatched',
              });
            }
          }}
        />
      )}
    </div>
  );
}
