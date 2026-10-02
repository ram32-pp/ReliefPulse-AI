'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { HeaderNavbar } from '@/components/navigation/HeaderNavbar';
import { getUserReportCode } from '@/lib/userReport';
import { Radio, Search, ShieldCheck, ArrowRight, Loader2, Phone } from 'lucide-react';

export default function StatusIndexPage() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [trackInput, setTrackInput] = useState('');

  useEffect(() => {
    const userCode = getUserReportCode();
    if (userCode) {
      router.replace(`/status/${userCode}`);
    } else {
      router.replace('/status/latest');
    }
  }, [router]);

  const handleTrackSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = trackInput.trim().replace(/^#/, '');
    if (clean) {
      router.push(`/status/${clean.toUpperCase()}`);
    } else {
      router.push('/status/latest');
    }
  };

  if (isChecking) {
    return (
      <div
        suppressHydrationWarning
        className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center text-slate-400 text-xs gap-3 font-sans"
      >
        <Loader2 className="animate-spin text-sky-blue" size={24} />
        <span>Checking for active emergency reports...</span>
      </div>
    );
  }

  return (
    <div
      suppressHydrationWarning
      className="min-h-screen flex flex-col items-center relative overflow-x-hidden pb-20 font-sans"
    >
      {/* Dynamic Background */}
      <div
        suppressHydrationWarning
        className="fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,176,255,0.12),transparent_45%),radial-gradient(circle_at_bottom,_rgba(255,42,76,0.12),transparent_40%)] -z-20 pointer-events-none"
      />

      {/* Global Header */}
      <div
        suppressHydrationWarning
        className="w-full max-w-5xl mx-auto px-3 sm:px-6 pt-2 sm:pt-4 mb-6"
      >
        <HeaderNavbar />
      </div>

      <main className="w-full max-w-lg mx-auto px-4 flex flex-col items-center text-center">
        {/* No Active Request Card */}
        <div className="w-full glass rounded-3xl p-6 sm:p-8 border border-white/15 shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-sky-blue/15 text-sky-blue border border-sky-blue/30 flex items-center justify-center mx-auto mb-4">
            <ShieldCheck size={32} />
          </div>

          <h1 className="text-xl sm:text-2xl font-black text-warm-white mb-2">
            No Active Emergency Request
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-6">
            You have not submitted an emergency broadcast from this device. If you or someone nearby is in immediate danger, broadcast an SOS request now.
          </p>

          <button
            type="button"
            onClick={() => router.push('/sos')}
            className="w-full bg-gradient-to-r from-pulse-red to-rose-600 hover:from-red-600 hover:to-rose-700 text-white font-black text-sm sm:text-base py-4 rounded-2xl shadow-[0_10px_30px_rgba(255,42,76,0.4)] active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer mb-6"
          >
            <Radio size={18} className="animate-pulse" />
            <span>BROADCAST EMERGENCY SOS NOW</span>
            <ArrowRight size={18} />
          </button>

          {/* Search by Incident Code Divider */}
          <div className="pt-5 border-t border-white/10 text-left">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block mb-2">
              Track Another Incident
            </span>
            <form onSubmit={handleTrackSubmit} className="flex gap-2">
              <input
                type="text"
                value={trackInput}
                onChange={(e) => setTrackInput(e.target.value)}
                placeholder="Enter incident code (e.g. RP-2847)"
                className="flex-grow bg-slate-900/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-xs text-warm-white placeholder:text-slate-500 focus:outline-none focus:border-sky-blue font-mono tabular-nums uppercase"
              />
              <button
                type="submit"
                disabled={!trackInput.trim()}
                className="px-4 py-2.5 rounded-xl bg-sky-blue text-slate-950 font-bold text-xs disabled:opacity-50 transition-all flex items-center gap-1.5 cursor-pointer shrink-0"
              >
                <Search size={14} />
                <span>Track</span>
              </button>
            </form>
          </div>
        </div>

        {/* Emergency Hotline Banner */}
        <div className="mt-5 w-full glass rounded-2xl p-4 border border-amber-alert/30 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-warm-white font-semibold">
            <Phone size={16} className="text-sky-blue" />
            <span>Emergency Services Hotline</span>
          </div>
          <a
            href="tel:1122"
            className="px-3 py-1.5 rounded-xl bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue font-bold text-xs border border-sky-blue/40 flex items-center gap-1.5 transition-all cursor-pointer"
          >
            <span>Call 1122</span>
          </a>
        </div>
      </main>
    </div>
  );
}
