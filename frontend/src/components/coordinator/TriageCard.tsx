'use client';

import React, { useState } from 'react';
import {
  AlertTriangle,
  Users,
  MapPin,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertCircle,
  Droplets,
  Flame,
  Building2,
  Stethoscope,
  Baby,
  Clock,
  Send,
} from 'lucide-react';
import { DispatchModal } from './DispatchModal';

interface MedicalRisk {
  type: string;
  count: number;
  detail?: string;
}

interface AnomalyFlag {
  flag_type: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
}

interface TriageCardProps {
  id: string;
  incidentCode: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  location: string;
  centroid?: { lat: number; lng: number };
  headcount: number;
  totalReports: number;
  timeAgo: string;
  hazardType: string;
  medicalRisks: MedicalRisk[];
  clusterConfidence: number;
  aiSummary?: string;
  aiReasoning: string[];
  anomalyFlags: AnomalyFlag[];
  representativeAudioUrl?: string;
  gpsTextMatch?: { level: string; confidence: number };
  isSelected?: boolean;
  onClick?: () => void;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onSkip?: (id: string) => void;
}

const hazardIcons: Record<string, React.ReactNode> = {
  flood: <Droplets size={14} className="text-sky-blue" />,
  fire: <Flame size={14} className="text-pulse-red" />,
  structural_collapse: <Building2 size={14} className="text-amber-alert" />,
  medical_emergency: <Stethoscope size={14} className="text-relief-green" />,
  earthquake: <AlertTriangle size={14} className="text-amber-alert" />,
};

export const TriageCard: React.FC<TriageCardProps> = ({
  id,
  incidentCode,
  severity,
  location,
  centroid,
  headcount,
  totalReports,
  timeAgo,
  hazardType,
  medicalRisks,
  clusterConfidence,
  aiSummary,
  aiReasoning,
  anomalyFlags,
  representativeAudioUrl,
  gpsTextMatch,
  isSelected,
  onClick,
  onApprove,
  onReject,
  onSkip,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showDispatch, setShowDispatch] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  const borderColors: Record<string, string> = {
    critical: 'border-l-pulse-red rtl:border-l-transparent rtl:border-r-pulse-red',
    high: 'border-l-amber-alert rtl:border-l-transparent rtl:border-r-amber-alert',
    medium: 'border-l-sky-blue rtl:border-l-transparent rtl:border-r-sky-blue',
    low: 'border-l-slate-400 rtl:border-l-transparent rtl:border-r-slate-400',
  };

  const badgeColors: Record<string, string> = {
    critical: 'bg-pulse-red/20 text-pulse-red border-pulse-red/40',
    high: 'bg-amber-alert/20 text-amber-alert border-amber-alert/40',
    medium: 'bg-sky-blue/20 text-sky-blue border-sky-blue/40',
    low: 'bg-slate-700/30 text-slate-300 border-slate-600',
  };

  const handleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  const confidencePercent = Math.round(clusterConfidence * 100);

  return (
    <>
      <div
        onClick={onClick}
        className={`glass rounded-xl border border-white/10 border-l-4 rtl:border-l-0 rtl:border-r-4 ${borderColors[severity]} shadow-lg cursor-pointer transition-all ${
          isSelected
            ? 'ring-2 ring-sky-blue bg-sky-blue/10 border-sky-blue/50 shadow-sky-blue/20'
            : 'hover:bg-white/5 hover:border-white/20'
        }`}
      >
        {/* Collapsed Header */}
        <div className="p-3.5">
          <div className="flex justify-between items-start mb-2">
            <div className="flex gap-2 items-center">
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border ${badgeColors[severity]}`}
              >
                {severity}
              </span>
              <span className="text-xs font-mono text-sky-blue font-bold">#{incidentCode}</span>
            </div>
            <span className="text-xs text-slate-400 flex items-center gap-1 font-mono" suppressHydrationWarning>
              <Clock size={12} /> {timeAgo}
            </span>
          </div>

          <h4 className="font-bold text-warm-white text-sm mb-1.5 flex items-center gap-1.5">
            <MapPin size={15} className="text-pulse-red shrink-0" />
            <span className="truncate">{location}</span>
          </h4>

          {/* Key metrics row */}
          <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-xs text-slate-300 mb-2.5">
            <span className="flex items-center gap-1">
              <Users size={13} className="text-slate-400" /> {headcount} people
            </span>
            <span className="flex items-center gap-1">
              {hazardIcons[hazardType] || <AlertTriangle size={13} />}
              <span className="capitalize">{hazardType.replace(/_/g, ' ')}</span>
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {totalReports} reports
            </span>
          </div>

          {/* Medical risks chips */}
          {medicalRisks.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              {medicalRisks.map((risk, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-pulse-red/15 border border-pulse-red/30 text-rose-300 font-medium"
                >
                  {risk.type === 'infant' && <Baby size={11} />}
                  {risk.type === 'elderly' && '👴'}
                  {risk.type === 'pregnant' && '🤰'}
                  {risk.type === 'injured' && '🩹'}
                  <span>{risk.count}x {risk.type}{risk.detail ? ` (${risk.detail})` : ''}</span>
                </span>
              ))}
            </div>
          )}

          {/* Confidence bar */}
          <div className="flex items-center gap-2 mb-2.5">
            <span className="text-[10px] text-slate-400 font-medium shrink-0">AI Match</span>
            <div className="flex-grow h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  clusterConfidence >= 0.8
                    ? 'bg-relief-green'
                    : clusterConfidence >= 0.5
                    ? 'bg-amber-alert'
                    : 'bg-pulse-red'
                }`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-slate-400 shrink-0">{confidencePercent}%</span>
          </div>

          {/* GPS match indicator */}
          {gpsTextMatch && (
            <div className="flex items-center gap-1.5 text-[11px] mb-2.5 text-slate-300">
              {gpsTextMatch.level === 'exact' || gpsTextMatch.level === 'neighborhood' ? (
                <CheckCircle size={13} className="text-relief-green" />
              ) : (
                <AlertCircle size={13} className="text-amber-alert" />
              )}
              <span>
                GPS ↔ Text: <span className="font-semibold capitalize text-warm-white">{gpsTextMatch.level}</span> ({Math.round(gpsTextMatch.confidence * 100)}%)
              </span>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowDispatch(true);
              }}
              className="flex-grow bg-gradient-to-r from-relief-green to-emerald-600 text-slate-950 text-xs font-bold py-2 rounded-lg shadow hover:shadow-relief-green/30 transition-all flex items-center justify-center gap-1.5 active:scale-95 cursor-pointer"
            >
              <Send size={13} /> Dispatch
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSkip?.(id);
              }}
              className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-slate-300 text-xs font-medium border border-white/10 transition-colors cursor-pointer"
              title="Skip for later"
            >
              ⏭️
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onReject?.(id);
              }}
              className="px-3 py-2 bg-pulse-red/20 hover:bg-pulse-red/30 rounded-lg text-pulse-red text-xs font-medium border border-pulse-red/30 transition-colors cursor-pointer"
              title="Reject false signal"
            >
              <XCircle size={14} />
            </button>
            <button
              onClick={handleExpand}
              className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-slate-300 border border-white/10 cursor-pointer"
              title="Toggle details"
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        </div>

        {/* Expanded Detail */}
        {expanded && (
          <div className="px-3.5 pb-3.5 pt-2 border-t border-white/10 text-xs space-y-3">
            {/* AI Summary */}
            {aiSummary && (
              <div className="bg-white/5 rounded-lg p-2.5 border border-white/10">
                <span className="text-[10px] font-bold text-sky-blue uppercase tracking-wider block mb-1">
                  Situation Summary
                </span>
                <p className="text-slate-300 leading-relaxed">{aiSummary}</p>
              </div>
            )}

            {/* AI Reasoning */}
            {aiReasoning.length > 0 && (
              <div>
                <span className="text-[10px] font-bold text-amber-alert uppercase tracking-wider block mb-1.5">
                  AI Triage Reasoning
                </span>
                <ul className="space-y-1">
                  {aiReasoning.map((reason, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-slate-300">
                      <span className="text-relief-green shrink-0">•</span>
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Audio Playback */}
            {representativeAudioUrl && (
              <div className="bg-white/5 rounded-lg p-2.5 flex items-center gap-3 border border-white/10">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsPlaying(!isPlaying);
                  }}
                  className="bg-sky-blue text-slate-950 p-2 rounded-full shrink-0 hover:bg-sky-400 transition-colors cursor-pointer"
                >
                  {isPlaying ? <Pause size={13} /> : <Play size={13} className="ml-0.5" />}
                </button>
                <div className="flex-grow">
                  <div className="h-1.5 bg-white/10 rounded-full mb-1 overflow-hidden">
                    <div className="h-full bg-sky-blue rounded-full w-2/5 animate-pulse" />
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">Representative voice signal</span>
                </div>
              </div>
            )}

            {/* Anomaly Flags */}
            {anomalyFlags.length > 0 && (
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Anomaly Flags
                </span>
                {anomalyFlags.map((flag, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-1.5 text-xs p-1.5 rounded-md mb-1 ${
                      flag.severity === 'critical'
                        ? 'text-pulse-red bg-pulse-red/10'
                        : flag.severity === 'warning'
                        ? 'text-amber-alert bg-amber-alert/10'
                        : 'text-slate-400 bg-white/5'
                    }`}
                  >
                    <span>{flag.severity === 'critical' ? '🚨' : flag.severity === 'warning' ? '⚠️' : 'ℹ️'}</span>
                    <span>{flag.description}</span>
                  </div>
                ))}
              </div>
            )}

            {anomalyFlags.length === 0 && (
              <div className="flex items-center gap-1.5 text-xs text-relief-green">
                <CheckCircle size={14} /> No anomalies or spoofing detected
              </div>
            )}
          </div>
        )}
      </div>

      {showDispatch && (
        <DispatchModal
          onClose={() => setShowDispatch(false)}
          incidentId={id}
          hazardType={hazardType}
          locationName={location}
          onSuccess={() => {
            setShowDispatch(false);
          }}
        />
      )}
    </>
  );
};

export default TriageCard;
