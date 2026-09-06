'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n';
import { Radio } from 'lucide-react';

interface PulseButtonProps {
  onClick: () => void;
}

export const PulseButton: React.FC<PulseButtonProps> = ({ onClick }) => {
  const { t } = useTranslation();

  return (
    <div suppressHydrationWarning className="relative w-64 h-64 mx-auto flex items-center justify-center my-6">
      {/* Ambient Pulsing Glow Rings */}
      <div className="absolute inset-0 rounded-full bg-pulse-red/30 animate-ripple-slow pointer-events-none blur-md"></div>
      <div
        className="absolute inset-3 rounded-full bg-rose-500/40 animate-ripple-fast pointer-events-none blur-sm"
        style={{ animationDelay: '0.4s' }}
      ></div>

      {/* Cyber Reticle Outer Ring */}
      <div className="absolute -inset-3 rounded-full border border-pulse-red/40 animate-spin pointer-events-none" style={{ animationDuration: '25s' }}>
        <div className="w-2 h-2 rounded-full bg-sky-blue absolute top-0 left-1/2 -translate-x-1/2"></div>
      </div>

      {/* Main SOS Trigger Button */}
      <button
        onClick={onClick}
        className="relative z-10 flex flex-col items-center justify-center w-full h-full rounded-full bg-gradient-to-tr from-pulse-red via-red-600 to-rose-500 text-white shadow-[0_0_60px_rgba(255,42,76,0.7),inset_0_-8px_20px_rgba(0,0,0,0.4),inset_0_8px_20px_rgba(255,255,255,0.4)] transition-all duration-300 active:scale-90 group animate-floating border-4 border-white/20 cursor-pointer"
        aria-label={t('sos_button_primary') || 'Broadcast Emergency SOS'}
      >
        <div className="absolute inset-0 rounded-full bg-pulse-red animate-heartbeat opacity-50 -z-10 group-active:animate-none"></div>

        <Radio size={28} className="animate-pulse mb-1 text-amber-alert drop-shadow" />

        <span className="text-5xl font-black tracking-widest leading-none drop-shadow-lg text-white">
          SOS
        </span>

        <span className="mt-2 text-xs font-black uppercase tracking-widest text-slate-100 bg-black/30 px-3 py-1 rounded-full border border-white/20">
          {t('sos_button_secondary') || 'TAP FOR HELP'}
        </span>
      </button>
    </div>
  );
};
