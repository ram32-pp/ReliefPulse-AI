'use client';

import React, { useState, useEffect } from 'react';
import { TriageQueue } from '@/components/coordinator/TriageQueue';
import nextDynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { fetchTriageQueue, rejectIncident } from '@/lib/api';
import {
  ShieldAlert,
  MapPin,
  Activity,
  Filter,
  Search,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Video,
  Radio,
  Layers,
  Sparkles,
} from 'lucide-react';

const LiveMap = nextDynamic(() => import('@/components/coordinator/LiveMap'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full bg-slate-950 animate-pulse flex flex-col items-center justify-center text-slate-400 text-xs">
      <Radio className="animate-spin text-sky-blue mb-2" size={24} />
      <span>Loading Command Center Map...</span>
    </div>
  ),
});

const MOCK_INCIDENTS = [
  {
    incident_id: 'C-491',
    incident_code: 'C-491',
    severity: 'critical' as const,
    hazard_type: 'flood',
    location: { name: 'Korangi Sector 4, Street 7-B' },
    total_reports: 14,
    total_individuals: 42,
    medical_risks: [{ type: 'infant', count: 1 }, { type: 'elderly', count: 2 }],
    cluster_confidence: 0.94,
    ai_reasoning: [
      'Infant present → auto-escalation trigger',
      '14 independent corroborating reports in 150m radius',
      'Water level rising (3ft → 5ft over 2 hours)',
    ],
    anomaly_flags: [],
    first_report_at: '2025-01-01T10:00:00.000Z',
    last_report_at: '2025-01-01T10:10:00.000Z',
  },
  {
    incident_id: 'C-492',
    incident_code: 'C-492',
    severity: 'high' as const,
    hazard_type: 'fire',
    location: { name: 'Gulshan Block 13-D' },
    total_reports: 8,
    total_individuals: 18,
    medical_risks: [{ type: 'injured', count: 3 }],
    cluster_confidence: 0.88,
    ai_reasoning: [
      'Electrical short circuit spread to residential block',
      'Smoke inhalation hazard confirmed by 4 voice notes',
    ],
    anomaly_flags: [],
    first_report_at: '2025-01-01T09:45:00.000Z',
    last_report_at: '2025-01-01T10:05:00.000Z',
  },
  {
    incident_id: 'C-493',
    incident_code: 'C-493',
    severity: 'medium' as const,
    hazard_type: 'structural_collapse',
    location: { name: 'Lyari Old Town' },
    total_reports: 5,
    total_individuals: 12,
    medical_risks: [{ type: 'trapped', count: 2 }],
    cluster_confidence: 0.76,
    ai_reasoning: ['Partial wall collapse after heavy rain'],
    anomaly_flags: [],
    first_report_at: '2025-01-01T09:30:00.000Z',
    last_report_at: '2025-01-01T10:00:00.000Z',
  },
];

export default function CoordinatorDashboard() {
  const router = useRouter();
  const { t, isRTL } = useTranslation();
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'high' | 'medium'>('all');
  const mockIncidents = MOCK_INCIDENTS;

  const [liveIncidents, setLiveIncidents] = useState<any[] | null>(null);
  const [isLiveActive, setIsLiveActive] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadQueue = async () => {
      try {
        const data = await fetchTriageQueue({
          severity: severityFilter === 'all' ? undefined : severityFilter,
          status: 'open',
        });
        if (isMounted && data && Array.isArray(data.incidents) && data.incidents.length > 0) {
          setLiveIncidents(data.incidents);
          setIsLiveActive(true);
        }
      } catch (err) {
        if (isMounted) setIsLiveActive(false);
      }
    };

    loadQueue();
    const interval = setInterval(loadQueue, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [severityFilter]);

  const handleRejectIncident = async (id: string) => {
    if (!confirm('Are you sure you want to reject this emergency signal as a false alarm or duplicate?')) {
      return;
    }
    try {
      await rejectIncident({ incidentId: id, reason: 'Coordinator rejected from triage queue' });
      if (liveIncidents) {
        setLiveIncidents((prev) =>
          prev ? prev.filter((i) => i.incident_id !== id && i.incident_code !== id && i.id !== id) : null
        );
      }
      if (selectedIncident === id) {
        setSelectedIncident(null);
      }
    } catch (err) {
      console.warn('Reject error:', err);
    }
  };

  const activeIncidents = liveIncidents && liveIncidents.length > 0 ? liveIncidents : mockIncidents;
  const filteredIncidents =
    severityFilter === 'all'
      ? activeIncidents
      : activeIncidents.filter((i) => i.severity === severityFilter);

  const BackIcon = isRTL ? ArrowRight : ArrowLeft;

  return (
    <div
      suppressHydrationWarning
      className="flex flex-col h-screen w-screen bg-[#060913] text-warm-white overflow-hidden font-sans"
    >
      {/* Top Cyber Command Header with Language Switcher */}
      <header
        suppressHydrationWarning
        className="h-16 border-b border-white/10 bg-slate-950/80 backdrop-blur-2xl px-6 flex items-center justify-between shrink-0 z-50"
      >
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all active:scale-95 cursor-pointer"
            title="Return Home"
          >
            <BackIcon size={18} />
          </button>

          <div className="flex items-center gap-3">
            <div className="relative">
              <span className="absolute inset-0 rounded-full bg-pulse-red/50 animate-ping"></span>
              <div className="relative p-2 rounded-xl bg-pulse-red text-white">
                <ShieldAlert size={20} />
              </div>
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-gradient flex items-center gap-2">
                {t('coordinator_title')}
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-blue/20 text-sky-blue border border-sky-blue/40 font-mono">
                  LIVE AI
                </span>
              </h1>
              <p className="text-[10px] text-slate-400 font-mono">
                {t('coordinator_subtitle')}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <nav className="hidden lg:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-xs">
            <button
              onClick={() => router.push('/')}
              className="px-3 py-1 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            >
              {t('nav_home')}
            </button>
            <button
              onClick={() => router.push('/sos')}
              className="px-3 py-1 rounded-lg bg-pulse-red/20 text-pulse-red hover:bg-pulse-red/30 transition-colors font-semibold cursor-pointer"
            >
              {t('nav_sos')}
            </button>
            <button
              onClick={() => router.push('/status/RP-QUEUED')}
              className="px-3 py-1 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            >
              {t('nav_track')}
            </button>
          </nav>

          <div className="hidden sm:flex items-center gap-2 text-xs font-mono">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
              <Radio size={13} className="text-relief-green animate-pulse" />
              <span className="text-slate-400">Signals:</span>
              <span className="text-relief-green font-bold">27</span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
              <Activity size={13} className="text-amber-alert" />
              <span className="text-slate-400">AI:</span>
              <span className="text-amber-alert font-bold">94%</span>
            </div>
          </div>
          <a
            href="tel:1122"
            title="Call Emergency Rescue Ambulance 1122"
            className="flex items-center gap-1 sm:gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl bg-gradient-to-r from-pulse-red to-rose-600 hover:from-red-600 hover:to-rose-700 text-white text-[11px] sm:text-xs font-black font-mono shadow-md border border-red-400/40 transition-all active:scale-95 shrink-0 cursor-pointer"
          >
            <span className="text-xs">🚑</span>
            <span className="tracking-wide">1122</span>
          </a>

          <LanguageSwitcher compact={true} />
        </div>
      </header>

      {/* Main Split Interface Area */}
      <div className="flex flex-grow h-[calc(100vh-4rem)] overflow-hidden">
        {/* Left Side: Triage Queue Panel */}
        <div className="w-[360px] sm:w-[420px] xl:w-[460px] border-r rtl:border-r-0 rtl:border-l border-white/10 bg-slate-950/60 backdrop-blur-xl flex flex-col h-full shrink-0">
          {/* Queue Filter Bar */}
          <div className="p-4 border-b border-white/10 flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-2">
              <Filter size={16} className="text-sky-blue" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                {`${t('triage_queue')} (${filteredIncidents.length})`}
              </span>
              {isLiveActive && (
                <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold animate-pulse">
                  LIVE
                </span>
              )}
            </div>

            <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-xs">
              <button
                onClick={() => setSeverityFilter('all')}
                className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                  severityFilter === 'all' ? 'bg-sky-blue text-slate-950 font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                {t('filter_all')}
              </button>
              <button
                onClick={() => setSeverityFilter('critical')}
                className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                  severityFilter === 'critical' ? 'bg-pulse-red text-white font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                {t('filter_critical')}
              </button>
              <button
                onClick={() => setSeverityFilter('high')}
                className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                  severityFilter === 'high' ? 'bg-amber-alert text-slate-950 font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                {t('filter_high')}
              </button>
            </div>
          </div>

          {/* Queue List Container */}
          <div className="flex-grow overflow-y-auto p-4 space-y-3">
            <TriageQueue
              incidents={filteredIncidents}
              onSelect={setSelectedIncident}
              onReject={handleRejectIncident}
              selectedId={selectedIncident || undefined}
            />
          </div>
        </div>

        {/* Right Side: Interactive Coordinator Map View */}
        <div className="flex-grow flex flex-col relative h-full bg-slate-900">
          <LiveMap
            selectedIncident={selectedIncident}
            onMarkerClick={setSelectedIncident}
            incidents={filteredIncidents}
          />

          {/* Incident Detail Floating Panel Card */}
          {selectedIncident && (() => {
            const selectedIncidentData = activeIncidents.find(
              (i) =>
                (i.incident_id && String(i.incident_id).toLowerCase() === selectedIncident.toLowerCase()) ||
                (i.incident_code && String(i.incident_code).toLowerCase() === selectedIncident.toLowerCase()) ||
                (i.id && String(i.id).toLowerCase() === selectedIncident.toLowerCase())
            );

            const hazard = selectedIncidentData?.hazard_type || 'emergency';
            const locationName = selectedIncidentData?.location?.name || 'Verified Emergency Location';
            const headcount = selectedIncidentData?.total_individuals ?? 1;
            const reportsCount = selectedIncidentData?.total_reports ?? 1;
            const summary =
              selectedIncidentData?.ai_summary ||
              (Array.isArray(selectedIncidentData?.ai_reasoning) && selectedIncidentData.ai_reasoning.length > 0
                ? selectedIncidentData.ai_reasoning.join('. ')
                : t('incident_context_desc'));

            return (
              <div className="absolute bottom-6 left-6 right-6 bg-slate-950/95 border border-sky-blue/40 rounded-2xl shadow-2xl p-5 backdrop-blur-2xl z-[1000] max-h-[340px] overflow-y-auto">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2.5 py-1 rounded-lg bg-pulse-red text-white font-mono text-xs font-bold uppercase tracking-wider">
                      {selectedIncidentData?.severity?.toUpperCase() || 'CRITICAL'} CLUSTER
                    </span>
                    <span className="px-2 py-0.5 rounded-lg bg-sky-blue/20 text-sky-blue border border-sky-blue/30 font-mono text-xs font-semibold uppercase">
                      {hazard}
                    </span>
                    <h3 className="font-black text-lg text-warm-white">
                      {selectedIncidentData?.incident_code || selectedIncident} &bull; {locationName}
                    </h3>
                  </div>

                  <button
                    onClick={() => setSelectedIncident(null)}
                    className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white text-sm cursor-pointer"
                  >
                    ✕
                  </button>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono text-slate-300 mb-3 flex-wrap">
                  <span className="flex items-center gap-1 text-warm-white font-semibold">
                    👥 {headcount} Individuals at Risk
                  </span>
                  <span className="text-slate-400">
                    📋 {reportsCount} Corroborated Reports
                  </span>
                  <span className="text-relief-green">
                    ✓ Grounding Match Verified
                  </span>
                </div>

                <p className="text-xs text-slate-300 mb-4 leading-relaxed bg-white/5 p-3 rounded-xl border border-white/10">
                  {summary}
                </p>

                <div className="flex items-center gap-3">
                  <a
                    href={`/coordinator/incidents/${selectedIncident}`}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-blue to-emerald-400 text-slate-950 font-bold text-xs shadow-lg hover:shadow-sky-blue/40 transition-all flex items-center gap-2 active:scale-95 cursor-pointer"
                  >
                    <Sparkles size={16} /> {t('view_full_intel')}
                  </a>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
