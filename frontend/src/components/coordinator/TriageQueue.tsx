'use client';

import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { TriageCard } from './TriageCard';

interface Incident {
  incident_id: string;
  incident_code: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  hazard_type: string;
  location: { name?: string; centroid?: { lat: number; lng: number } };
  total_reports: number;
  total_individuals: number;
  medical_risks: { type: string; count: number; detail?: string }[];
  cluster_confidence: number;
  ai_summary?: string;
  ai_reasoning: string[];
  anomaly_flags: { flag_type: string; description: string; severity: 'info' | 'warning' | 'critical' }[];
  representative_audio_url?: string;
  first_report_at: string;
  last_report_at: string;
  gps_text_match?: { level: string; confidence: number };
  triage_tier?: string;
  cluster_density_factor?: number;
  device_integrity_score?: number;
  media_forensics_score?: number;
  semantic_consistency_score?: number;
  tamper_penalty?: number;
  verification_score?: number;
  callback_status?: string;
  verification_breakdown_5layer?: any;
}

interface TriageQueueProps {
  incidents: Incident[];
  selectedId?: string;
  onSelect?: (id: string) => void;
  onReject?: (id: string) => void;
  filterSeverity?: string;
  onFilterChange?: (severity: string) => void;
  onTriggerCallback?: (id: string) => Promise<void>;
}

function timeAgo(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return `${Math.floor(diffHrs / 24)}d ago`;
}

export const TriageQueue: React.FC<TriageQueueProps> = ({
  incidents,
  selectedId,
  onSelect,
  onReject,
  filterSeverity,
  onFilterChange,
  onTriggerCallback,
}) => {
  const severityFilters = ['all', 'critical', 'high', 'medium', 'low'];

  return (
    <div className="flex flex-col h-full">
      {/* Optional standalone filter tabs (only when onFilterChange is passed) */}
      {onFilterChange && (
        <div className="flex gap-1.5 px-3 py-2 border-b border-white/10 bg-slate-950/80 backdrop-blur-md sticky top-0 z-10">
          {severityFilters.map((sev) => (
            <button
              key={sev}
              onClick={() => onFilterChange(sev)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all capitalize cursor-pointer ${
                filterSeverity === sev
                  ? 'bg-sky-blue text-slate-950 font-bold'
                  : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      )}

      {/* Cards list */}
      <div className="flex-grow overflow-y-auto space-y-3 pr-1">
        {incidents.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center text-slate-400 py-20 px-4">
            <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-sky-blue/80 mb-3.5 shadow-inner">
              <ShieldCheck size={28} className="text-relief-green" />
            </div>
            <p className="text-sm font-bold text-warm-white">No Incidents in Queue</p>
            <p className="text-xs text-slate-400 mt-1 max-w-[260px] leading-relaxed">
              All emergency clusters have been triaged. Waiting for new live SOS broadcasts.
            </p>
          </div>
        )}
        {incidents.map((inc) => (
          <TriageCard
            key={inc.incident_id}
            id={inc.incident_id}
            incidentCode={inc.incident_code}
            severity={inc.severity}
            location={inc.location.name || 'Unknown Location'}
            centroid={inc.location.centroid}
            headcount={inc.total_individuals}
            totalReports={inc.total_reports}
            timeAgo={timeAgo(inc.last_report_at)}
            hazardType={inc.hazard_type}
            medicalRisks={inc.medical_risks}
            clusterConfidence={inc.cluster_confidence}
            aiSummary={inc.ai_summary}
            aiReasoning={inc.ai_reasoning}
            anomalyFlags={inc.anomaly_flags}
            representativeAudioUrl={inc.representative_audio_url}
            gpsTextMatch={inc.gps_text_match}
            triageTier={inc.triage_tier}
            clusterDensityFactor={inc.cluster_density_factor}
            deviceIntegrityScore={inc.device_integrity_score}
            mediaForensicsScore={inc.media_forensics_score}
            semanticConsistencyScore={inc.semantic_consistency_score}
            tamperPenalty={inc.tamper_penalty}
            verificationScore={inc.verification_score}
            callbackStatus={inc.callback_status}
            verificationBreakdown5layer={inc.verification_breakdown_5layer}
            isSelected={selectedId === inc.incident_id}
            onClick={() => onSelect?.(inc.incident_id)}
            onReject={onReject}
            onTriggerCallback={onTriggerCallback}
          />
        ))}
      </div>
    </div>
  );
};
