'use client';

import React, { useState, useMemo } from 'react';
import { useTranslation } from '@/lib/i18n';
import { ShieldAlert, CheckCircle, X, Send, Users, AlertTriangle, Loader2 } from 'lucide-react';
import { advanceReliefStatus } from '@/lib/api';

interface DispatchModalProps {
  onClose: () => void;
  incidentId: string;
  hazardType?: string;
  locationName?: string;
  onSuccess?: () => void;
}

export const DispatchModal: React.FC<DispatchModalProps> = ({
  onClose,
  incidentId,
  hazardType = 'flood',
  locationName,
  onSuccess,
}) => {
  const { t } = useTranslation();

  const hazardKey = (hazardType || 'general').toLowerCase();

  const { defaultTeams, defaultEquipment } = useMemo(() => {
    if (hazardKey.includes('fire') || hazardKey.includes('smoke')) {
      return {
        defaultTeams: [
          'Karachi Fire Department Unit #9 (Nearest - 1.2km, Fast Extinguishment)',
          'Rescue 1122 Smoke & Evacuation Squad (2.4km)',
          'High-Rise Aerial Ladder Tender #3 (4.0km)',
        ],
        defaultEquipment: [
          'High-Pressure Water/Foam Hoses & Hydrant Boosters',
          'Self-Contained Breathing Apparatus (SCBA) & Oxygen Masks',
          'Thermal Imaging Smoke Camera & Portable Ventilation Blowers',
        ],
      };
    } else if (
      hazardKey.includes('collapse') ||
      hazardKey.includes('earthquake') ||
      hazardKey.includes('structural')
    ) {
      return {
        defaultTeams: [
          'Urban Search & Rescue Squad #2 (Nearest - 2.0km, Structural Extrication)',
          'Rescue 1122 Heavy Extrication & Shoring Unit (3.1km)',
          'Mobile Field Trauma Paramedic Unit (3.5km)',
        ],
        defaultEquipment: [
          'Hydraulic Cutters, Spreaders & Pneumatic Lifting Bags',
          'Acoustic Debris Listening Sensors & Snake Inspection Cameras',
          'Heavy Timber Shoring & Structural Support Props',
        ],
      };
    } else if (hazardKey.includes('medical') || hazardKey.includes('heat')) {
      return {
        defaultTeams: [
          'Rescue 1122 Advanced Life Support Ambulance #1 (Nearest - 1.5km)',
          'Paramedic Rapid Response Bike Squad (0.8km)',
          'Emergency Heatstroke / Field Triage Unit (2.2km)',
        ],
        defaultEquipment: [
          'Advanced Cardiac Life Support & Automated Defibrillator',
          'Pediatric & Adult Trauma First Aid Kits',
          'Portable Medical Oxygen Concentrators & IV Fluid Coolers',
        ],
      };
    } else {
      // Default: Flood / Inundation
      return {
        defaultTeams: [
          'Rescue 1122 Rapid Boat Unit #4 (Nearest - 1.8km, Flood Rescue)',
          'Rescue 1122 Medical Paramedic Unit (3.5km)',
          'Heavy Urban Search & Rescue Team (5.0km)',
        ],
        defaultEquipment: [
          'Inflatable Rescue Boats & Life Vests (Flood Inundation)',
          'Infant & Pediatric Trauma First Aid Kit',
          'Emergency Satellite Communication Transceiver',
        ],
      };
    }
  }, [hazardKey]);

  const [selectedTeam, setSelectedTeam] = useState(defaultTeams[0]);
  const [priority, setPriority] = useState('P0 - Immediate Life Threat (Auto Escalated)');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await advanceReliefStatus({
        incidentId,
        reliefStatus: 'dispatched',
        teamName: selectedTeam,
        etaMinutes: 15,
      });
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.warn('Dispatch API call fallback:', err);
      if (onSuccess) onSuccess();
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-[2000] flex items-center justify-center p-4">
      <div className="bg-slate-950 border border-white/20 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden text-warm-white font-sans">
        <div className="bg-slate-900 border-b border-white/10 p-4 font-bold text-base flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-relief-green/20 text-relief-green">
              <Send size={16} />
            </span>
            <span>Approve Dispatch: #{incidentId}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          {locationName && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-2.5 text-[11px] text-slate-300">
              <span className="text-slate-400 font-semibold uppercase text-[10px] block">Target Location:</span>
              <span className="text-warm-white font-medium">{locationName}</span>
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Assign to Team
            </label>
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl p-2.5 text-xs text-warm-white focus:ring-1 focus:ring-sky-blue focus:border-sky-blue outline-none"
            >
              {defaultTeams.map((team, idx) => (
                <option key={idx} value={team}>
                  {team}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Priority Level
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl p-2.5 text-xs text-warm-white focus:ring-1 focus:ring-sky-blue focus:border-sky-blue outline-none"
            >
              <option>P0 - Immediate Life Threat (Auto Escalated)</option>
              <option>P1 - High Urgency</option>
              <option>P2 - Medium Standard</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Required Equipment (Tailored for {hazardType.toUpperCase()})
            </label>
            <div className="space-y-2 text-slate-300 bg-white/5 p-3 rounded-xl border border-white/10">
              {defaultEquipment.map((equip, idx) => (
                <label key={idx} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked
                    className="rounded border-white/20 text-relief-green focus:ring-0"
                  />
                  <span>{equip}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Coordinator Dispatch Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl p-2.5 h-20 text-xs text-warm-white placeholder:text-slate-500 focus:ring-1 focus:ring-sky-blue focus:border-sky-blue outline-none"
              placeholder="Add specific instructions for response unit (e.g. Approach from North side, avoid flooded underpass)..."
            />
          </div>
        </div>

        <div className="bg-slate-900/90 p-4 border-t border-white/10 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-400 font-semibold hover:text-white hover:bg-white/10 rounded-xl transition-all cursor-pointer text-xs"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="px-5 py-2.5 bg-gradient-to-r from-relief-green to-emerald-600 hover:from-emerald-500 hover:to-emerald-700 text-slate-950 font-black rounded-xl shadow-lg transition-all active:scale-95 cursor-pointer text-xs flex items-center gap-1.5"
          >
            {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
            <span>CONFIRM DISPATCH</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default DispatchModal;
