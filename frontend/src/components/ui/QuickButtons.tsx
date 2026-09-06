'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n';
import { Check } from 'lucide-react';

interface QuickButtonsProps {
  onSelect: (type: string) => void;
  selectedTypes?: string[];
}

export const QuickButtons: React.FC<QuickButtonsProps> = ({ onSelect, selectedTypes = [] }) => {
  const { t } = useTranslation();

  const buttons = [
    { id: 'rising_floodwater', icon: '🌊', label: 'Rising Floodwater' },
    { id: 'structural_collapse', icon: '🏚️', label: 'Structural Collapse' },
    { id: 'active_fire', icon: '🔥', label: 'Active Fire' },
    { id: 'medical_emergency', icon: '🩺', label: 'Medical Emergency' },
    { id: 'trapped_people', icon: '🆘', label: 'Trapped People' },
  ];

  return (
    <div className="w-full glass rounded-3xl p-5 border border-white/15 shadow-xl">
      <h3 className="text-xs uppercase tracking-widest font-bold text-slate-300 mb-3 flex items-center justify-between">
        <span>{t('quick_buttons_title') || 'Select Active Hazard Badges'}</span>
        <span className="text-[10px] text-sky-blue font-mono font-medium">{t('select_all_apply') || 'Select all that apply'}</span>
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {buttons.map((btn) => {
          const isSelected = selectedTypes.includes(btn.id) || selectedTypes.includes(btn.label);
          return (
            <button
              key={btn.id}
              type="button"
              onClick={() => onSelect(btn.id)}
              className={`flex items-center justify-between p-3 rounded-2xl border transition-all duration-300 active:scale-95 text-left rtl:text-right cursor-pointer ${
                isSelected
                  ? 'border-pulse-red bg-pulse-red/20 shadow-[0_0_25px_rgba(255,42,76,0.35)] ring-1 ring-pulse-red'
                  : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20'
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="text-xl shrink-0">{btn.icon}</span>
                <span className="text-xs font-bold text-warm-white truncate">{btn.label}</span>
              </div>

              {isSelected && (
                <div className="p-0.5 rounded-full bg-pulse-red text-white shrink-0 ml-1">
                  <Check size={12} />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default QuickButtons;
