'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import {
  ShieldCheck,
  Radio,
  ArrowLeft,
  Phone,
  Activity,
} from 'lucide-react';

interface CoordinatorNavbarProps {
  className?: string;
  totalIncidents?: number;
}

export const CoordinatorNavbar: React.FC<CoordinatorNavbarProps> = ({
  className = '',
  totalIncidents,
}) => {
  const router = useRouter();
  const { t } = useTranslation();

  return (
    <header suppressHydrationWarning className={`w-full z-50 ${className}`}>
      <div
        suppressHydrationWarning
        className="glass rounded-2xl border border-white/15 px-3 sm:px-5 py-2.5 shadow-2xl backdrop-blur-2xl flex items-center justify-between gap-2 sm:gap-4 overflow-hidden"
      >
        {/* Brand Logo, Redesigned Name & Coordinator Badge */}
        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <div
            onClick={() => router.push('/coordinator')}
            className="flex items-center gap-2.5 sm:gap-3 cursor-pointer group"
          >
            <div className="relative flex items-center justify-center shrink-0">
              <div className="absolute -inset-1 rounded-2xl bg-gradient-to-tr from-[#FF4D6D]/30 via-transparent to-cyan-400/30 blur-sm group-hover:scale-110 transition-all opacity-80 group-hover:opacity-100" />
              <div className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-xl overflow-hidden p-1 bg-gradient-to-b from-[#131e3a] to-[#0a1020] border border-white/15 shadow-xl backdrop-blur-md flex items-center justify-center group-hover:scale-105 group-hover:border-cyan-400/40 transition-all">
                <img
                  src="/logo.png"
                  alt="ReliefPulse AI Logo"
                  className="w-full h-full object-contain filter drop-shadow-[0_0_8px_rgba(255,77,109,0.35)]"
                />
              </div>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <div className="flex items-baseline tracking-tight select-none">
                <span className="text-[15px] sm:text-[17px] font-black text-white tracking-tight drop-shadow-sm">
                  Relief
                </span>
                <span className="text-[15px] sm:text-[17px] font-black bg-gradient-to-r from-[#FF4D6D] via-[#FF6B6B] to-[#FF8E53] bg-clip-text text-transparent tracking-tight">
                  Pulse
                </span>
              </div>
              <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-gradient-to-r from-cyan-500/15 to-blue-500/15 border border-cyan-400/40 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.25)]">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shrink-0" />
                <span className="text-[9px] sm:text-[10px] font-mono font-black tracking-wider uppercase">
                  AI
                </span>
              </div>
            </div>
          </div>

          {/* Distinct Coordinator Command Tag */}
          <div className="hidden md:flex items-center gap-2 pl-3 border-l border-white/10">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-500/10 border border-sky-400/30 text-sky-300 text-xs font-mono font-bold tracking-wide">
              <ShieldCheck size={14} className="text-sky-400" />
              <span>COORDINATOR COMMAND</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-400/25 text-emerald-400 text-[11px] font-mono font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>LIVE NETWORK</span>
              {totalIncidents !== undefined && (
                <span className="px-1.5 py-0.2 bg-emerald-500/20 rounded font-bold">
                  {totalIncidents}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right Navigation & Control Actions */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Switch to Citizen UI button */}
          <button
            type="button"
            onClick={() => router.push('/')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white text-xs font-semibold transition-all cursor-pointer"
            title="Return to Citizen Portal"
          >
            <ArrowLeft size={13} className="text-slate-400 rtl:rotate-180" />
            <span className="hidden sm:inline">Citizen Portal</span>
            <span className="sm:hidden">Exit</span>
          </button>

          {/* 1122 Helpline Quick-Dial */}
          <a
            href="tel:1122"
            title="Call Emergency Rescue 1122"
            className="flex items-center gap-1 sm:gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl bg-gradient-to-r from-pulse-red to-rose-600 hover:from-red-600 hover:to-rose-700 text-white text-[11px] sm:text-xs font-black font-mono tabular-nums shadow-md border border-red-400/40 transition-all active:scale-95 shrink-0 cursor-pointer"
          >
            <span className="text-xs">🚑</span>
            <span className="tracking-wide">1122</span>
          </a>

          {/* Language Switcher */}
          <div className="shrink-0">
            <LanguageSwitcher compact={true} />
          </div>
        </div>
      </div>
    </header>
  );
};

export default CoordinatorNavbar;
