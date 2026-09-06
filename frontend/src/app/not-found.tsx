import React from 'react';
import Link from 'next/link';
import { ShieldAlert, Home, LifeBuoy, ArrowLeft, Phone } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#070b14] text-warm-white flex flex-col items-center justify-center px-4 py-12">
      <div className="max-w-md w-full glass rounded-3xl p-8 border border-white/10 shadow-2xl text-center">
        <div className="inline-flex p-4 rounded-2xl bg-pulse-red/15 text-pulse-red mb-6 border border-pulse-red/30">
          <ShieldAlert size={42} className="animate-pulse" />
        </div>

        <h1 className="text-3xl font-black tracking-tight mb-2">404 - Signal Not Found</h1>
        <p className="text-sm text-slate-400 mb-8 leading-relaxed">
          The requested emergency channel, report code, or coordinator node does not exist or has been relocated.
        </p>

        <div className="space-y-3 mb-8">
          <Link
            href="/"
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-sky-blue text-slate-950 font-bold text-sm hover:bg-sky-400 transition-all shadow-md active:scale-95"
          >
            <Home size={16} />
            <span>Return to Citizen Portal</span>
          </Link>

          <Link
            href="/sos"
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-pulse-red text-white font-bold text-sm hover:bg-red-600 transition-all shadow-md active:scale-95"
          >
            <LifeBuoy size={16} />
            <span>Broadcast Emergency SOS</span>
          </Link>

          <Link
            href="/coordinator"
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-white/10 text-slate-200 font-semibold text-sm hover:bg-white/20 transition-all active:scale-95"
          >
            <ArrowLeft size={16} />
            <span>Rescue Command Center</span>
          </Link>
        </div>

        <div className="pt-6 border-t border-white/10 text-xs text-slate-400">
          <p className="font-semibold uppercase tracking-wider text-[10px] text-slate-400 mb-2">
            Emergency Direct Dispatch
          </p>
          <div className="flex justify-center gap-4 text-slate-300 font-mono">
            <a href="tel:1122" className="flex items-center gap-1 hover:text-pulse-red">
              <Phone size={12} /> 1122 Rescue
            </a>
            <span className="text-slate-600">&bull;</span>
            <a href="tel:115" className="flex items-center gap-1 hover:text-amber-alert">
              <Phone size={12} /> 115 Edhi
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
