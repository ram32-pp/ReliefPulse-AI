'use client';

import React, { useState, useEffect } from 'react';
import { TriageQueue } from '@/components/coordinator/TriageQueue';
import nextDynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { CoordinatorNavbar } from '@/components/navigation/CoordinatorNavbar';
import { fetchTriageQueue, rejectIncident, triggerRapidCallback } from '@/lib/api';
import {
  MapPin,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Sparkles,
  ShieldCheck,
  Activity,
  PhoneCall,
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

export default function CoordinatorDashboard() {
  const router = useRouter();
  const { t, isRTL } = useTranslation();
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'open' | 'rejected'>('open');
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'high' | 'medium'>('all');
  const [triageTierFilter, setTriageTierFilter] = useState<'all' | 'verified_emergency' | 'suspected_unconfirmed' | 'flagged_or_prank'>('all');

  const [liveIncidents, setLiveIncidents] = useState<any[] | null>(null);
  const [isLiveActive, setIsLiveActive] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadQueue = async () => {
      try {
        const data = await fetchTriageQueue({
          severity: severityFilter === 'all' ? undefined : severityFilter,
          status: statusFilter,
          triage_tier: triageTierFilter === 'all' ? undefined : triageTierFilter,
        });
        if (isMounted && data && Array.isArray(data.incidents)) {
          setLiveIncidents(data.incidents);
          setIsLiveActive(true);
        }
      } catch (err) {
        if (isMounted) setIsLiveActive(false);
      }
    };

    loadQueue();
    const interval = setInterval(loadQueue, 4000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [severityFilter, statusFilter, triageTierFilter]);

  const handleTriggerCallback = async (id: string) => {
    try {
      await triggerRapidCallback({ incidentId: id, channel: 'auto' });
      const data = await fetchTriageQueue({
        severity: severityFilter === 'all' ? undefined : severityFilter,
        status: statusFilter,
        triage_tier: triageTierFilter === 'all' ? undefined : triageTierFilter,
      });
      if (data && Array.isArray(data.incidents)) {
        setLiveIncidents(data.incidents);
      }
    } catch (err) {
      console.error('Trigger callback error:', err);
    }
  };

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

  const activeIncidents = liveIncidents && liveIncidents.length > 0 ? liveIncidents : [];
  const filteredIncidents =
    severityFilter === 'all'
      ? activeIncidents
      : activeIncidents.filter((i) => i.severity === severityFilter);

  return (
    <div
      suppressHydrationWarning
      className="flex flex-col h-screen w-screen bg-[#060913] text-warm-white overflow-hidden font-sans"
    >
      {/* Dedicated Coordinator Command Navbar */}
      <div className="px-3 sm:px-6 py-2.5 shrink-0 z-50">
        <CoordinatorNavbar totalIncidents={activeIncidents.length} />
      </div>

      {/* Main Split Interface Area */}
      <div className="flex flex-grow overflow-hidden border-t border-white/10">
        {/* Left Side: Triage Queue Panel */}
        <div className="w-[360px] sm:w-[420px] xl:w-[460px] border-r rtl:border-r-0 rtl:border-l border-white/10 bg-slate-950/60 backdrop-blur-xl flex flex-col h-full shrink-0">
          {/* Queue Filter Bar */}
          <div className="p-3.5 border-b border-white/10 space-y-2.5 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Filter size={15} className="text-sky-blue" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  {statusFilter === 'open' ? t('triage_queue') : 'Flagged & Fake Reports'}{' '}
                  <span className="font-mono tabular-nums">({filteredIncidents.length})</span>
                </span>
                {isLiveActive && (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold animate-pulse">
                    LIVE
                  </span>
                )}
              </div>

              {/* Status Tab (Active vs Flagged/Fake) */}
              <div className="flex items-center gap-1 bg-white/5 p-0.5 rounded-xl border border-white/10 text-[11px]">
                <button
                  onClick={() => setStatusFilter('open')}
                  className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer font-medium ${
                    statusFilter === 'open'
                      ? 'bg-sky-blue text-slate-950 font-bold shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Active
                </button>
                <button
                  onClick={() => setStatusFilter('rejected')}
                  className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer font-medium ${
                    statusFilter === 'rejected'
                      ? 'bg-pulse-red text-white font-bold shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Fake / Spam
                </button>
              </div>
            </div>

            {/* 3-Tier Verification Routing Tabs */}
            <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-[11px] overflow-x-auto scrollbar-none">
              <button
                onClick={() => setTriageTierFilter('all')}
                className={`px-2 py-1 rounded-lg transition-all shrink-0 cursor-pointer font-medium ${
                  triageTierFilter === 'all'
                    ? 'bg-white/20 text-white font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                All Tiers
              </button>
              <button
                onClick={() => setTriageTierFilter('verified_emergency')}
                className={`px-2 py-1 rounded-lg transition-all shrink-0 cursor-pointer font-bold flex items-center gap-1 ${
                  triageTierFilter === 'verified_emergency'
                    ? 'bg-emerald-500/30 text-emerald-300 border border-emerald-500/50 shadow-sm'
                    : 'text-emerald-400/80 hover:text-emerald-300'
                }`}
                title="80-100 Score: Direct immediate dispatch"
              >
                <ShieldCheck size={11} className="text-emerald-400" />
                Verified (80-100)
              </button>
              <button
                onClick={() => setTriageTierFilter('suspected_unconfirmed')}
                className={`px-2 py-1 rounded-lg transition-all shrink-0 cursor-pointer font-bold flex items-center gap-1 ${
                  triageTierFilter === 'suspected_unconfirmed'
                    ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50 shadow-sm'
                    : 'text-amber-400/80 hover:text-amber-300'
                }`}
                title="35-79 Score: Rapid automated callback queue"
              >
                <Activity size={11} className="text-amber-400" />
                Callback (35-79)
              </button>
              <button
                onClick={() => setTriageTierFilter('flagged_or_prank')}
                className={`px-2 py-1 rounded-lg transition-all shrink-0 cursor-pointer font-bold flex items-center gap-1 ${
                  triageTierFilter === 'flagged_or_prank'
                    ? 'bg-rose-500/30 text-rose-300 border border-rose-500/50 shadow-sm'
                    : 'text-rose-400/80 hover:text-rose-300'
                }`}
                title="0-34 Score: Quarantined audit view"
              >
                <AlertTriangle size={11} className="text-rose-400" />
                Audit (0-34)
              </button>
            </div>

            {/* Severity Sub-Filter */}
            <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-xs w-fit">
              <button
                onClick={() => setSeverityFilter('all')}
                className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                  severityFilter === 'all' ? 'bg-white/20 text-warm-white font-bold' : 'text-slate-400 hover:text-white'
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
              onTriggerCallback={handleTriggerCallback}
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
