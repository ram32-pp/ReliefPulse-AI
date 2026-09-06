'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { HeaderNavbar } from '@/components/navigation/HeaderNavbar';
import { PulseButton } from '@/components/ui/PulseButton';
import { OfflineBadge } from '@/components/ui/OfflineBadge';
import {
  MapPin,
  ShieldAlert,
  Mic,
  Video,
  Radar,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Search,
  Sparkles,
  Radio,
  Clock,
  Compass,
  Phone,
  Droplets,
  Flame,
  Building2,
  Stethoscope,
  Baby,
  Activity,
  Send,
} from 'lucide-react';
import { useGeolocation } from '@/hooks/useGeolocation';
import { getUserReportCode } from '@/lib/userReport';

export default function Home() {
  const router = useRouter();
  const { t, isRTL } = useTranslation();
  const { coords } = useGeolocation();

  const [addressText, setAddressText] = useState('Detecting live coordinates...');
  const [trackCodeInput, setTrackCodeInput] = useState('');
  const [activeReportCode, setActiveReportCode] = useState<string | null>(null);
  const [selectedQuickHazards, setSelectedQuickHazards] = useState<string[]>([]);

  useEffect(() => {
    if (coords) {
      setAddressText(`${coords.latitude.toFixed(4)}° N, ${coords.longitude.toFixed(4)}° E (GPS Verified)`);
    }
  }, [coords]);

  useEffect(() => {
    setActiveReportCode(getUserReportCode());
    const onFocus = () => setActiveReportCode(getUserReportCode());
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, []);

  const handleSOS = (mode?: string) => {
    if (mode) {
      router.push(`/sos?mode=${mode}`);
    } else {
      router.push('/sos');
    }
  };

  const handleTrackSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = trackCodeInput.trim().replace(/^#/, '');
    if (clean) {
      router.push(`/status/${clean.toUpperCase()}`);
    } else if (activeReportCode) {
      router.push(`/status/${activeReportCode}`);
    } else {
      router.push('/status/latest');
    }
  };

  const toggleHazard = (key: string) => {
    if (selectedQuickHazards.includes(key)) {
      setSelectedQuickHazards(selectedQuickHazards.filter((k) => k !== key));
    } else {
      setSelectedQuickHazards([...selectedQuickHazards, key]);
    }
  };

  const ArrowIcon = isRTL ? ArrowLeft : ArrowRight;

  const quickHazards = [
    { key: 'flood', label: t('flood'), icon: Droplets, color: 'text-sky-blue' },
    { key: 'collapse', label: t('collapse'), icon: Building2, color: 'text-amber-alert' },
    { key: 'injured', label: t('injured'), icon: Stethoscope, color: 'text-pulse-red' },
    { key: 'fire', label: t('fire'), icon: Flame, color: 'text-rose-400' },
    { key: 'children', label: t('children'), icon: Baby, color: 'text-emerald-400' },
  ];

  return (
    <div suppressHydrationWarning className="min-h-screen flex flex-col items-center relative overflow-x-hidden pb-16 font-sans">
      {/* Dynamic Ambient Neon Lights */}
      <div suppressHydrationWarning className="fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,42,76,0.18),transparent_40%),radial-gradient(circle_at_bottom_right,_rgba(0,176,255,0.14),transparent_40%),radial-gradient(circle_at_bottom_left,_rgba(0,230,118,0.1),transparent_35%)] -z-20 pointer-events-none" />

      {/* Global Unified Header Navigation with Spacious Width */}
      <div suppressHydrationWarning className="w-full max-w-5xl mx-auto px-3 sm:px-6 pt-2 sm:pt-4 mb-4 sm:mb-6">
        <HeaderNavbar />
      </div>

      {/* Main Content Area */}
      <main suppressHydrationWarning className="w-full max-w-2xl mx-auto px-3 sm:px-4 flex flex-col items-center">
        {/* Hero Primary Emergency Card */}
        <section suppressHydrationWarning className="w-full glass rounded-3xl p-6 sm:p-8 mb-5 border border-white/15 text-center relative overflow-hidden shadow-2xl">
        {/* Offline Sentinel Badge */}
        <div className="absolute top-4 right-4 rtl:left-4 rtl:right-auto z-10">
          <OfflineBadge />
        </div>

        {/* Live GPS Telemetry Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-[11px] text-slate-300 font-mono mb-4">
          <MapPin size={12} className="text-pulse-red animate-pulse shrink-0" />
          <span className="truncate max-w-[240px] sm:max-w-[320px]">{addressText}</span>
        </div>

        {/* Hero Title & Description */}
        <h2 className="text-2xl sm:text-4xl font-black text-warm-white tracking-tight leading-tight mb-2">
          {t('sos_hero_title')}
        </h2>
        <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto leading-relaxed mb-6">
          {t('sos_hero_desc')}
        </p>

        {/* Big Tactile Pulse Emergency Button */}
        <div className="flex justify-center my-4 py-2">
          <PulseButton onClick={() => handleSOS()} />
        </div>

        {/* One-Touch Quick Hazard Tags */}
        <div className="mt-4 pt-4 border-t border-white/10">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block mb-2.5">
            {t('quick_buttons_title')}
          </span>
          <div className="flex flex-wrap items-center justify-center gap-1.5 sm:gap-2">
            {quickHazards.map((h) => {
              const Icon = h.icon;
              const isSelected = selectedQuickHazards.includes(h.key);

              return (
                <button
                  key={h.key}
                  type="button"
                  onClick={() => toggleHazard(h.key)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer active:scale-95 ${
                    isSelected
                      ? 'bg-pulse-red text-white shadow-lg border border-red-400/40'
                      : 'bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10'
                  }`}
                >
                  <Icon size={14} className={isSelected ? 'text-white' : h.color} />
                  <span>{h.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* Active User Report Banner (Only shown if user has an active report) */}
      {activeReportCode && (
        <div className="w-full mb-5 p-4 rounded-2xl bg-sky-blue/15 border border-sky-blue/30 flex items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2.5 rounded-xl bg-sky-blue text-slate-950 font-bold shrink-0">
              <Clock size={18} />
            </div>
            <div className="min-w-0">
              <span className="text-[10px] font-mono uppercase tracking-wider text-sky-300 font-bold block">
                Your Active Emergency Request
              </span>
              <span className="text-sm font-black text-warm-white font-mono block truncate">
                #{activeReportCode}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => router.push(`/status/${activeReportCode}`)}
            className="px-4 py-2 rounded-xl bg-sky-blue hover:bg-sky-400 text-slate-950 text-xs font-bold transition-all shrink-0 active:scale-95 cursor-pointer shadow-md"
          >
            Track Status &rarr;
          </button>
        </div>
      )}

      {/* 3 Focused Direct Action Cards (Voice SOS, Pinpoint Location, Text SOS) */}
      <section className="w-full mb-5">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Card 1: Voice SOS */}
          <div
            onClick={() => handleSOS('voice')}
            className="glass glass-hover rounded-2xl p-4 sm:p-5 text-left rtl:text-right cursor-pointer group border border-white/10 relative overflow-hidden flex flex-col justify-between min-h-[150px]"
          >
            <div>
              <div className="inline-flex p-3 rounded-xl bg-pulse-red/15 text-pulse-red border border-pulse-red/30 group-hover:scale-110 transition-transform mb-3">
                <Mic size={22} />
              </div>
              <h3 className="text-sm font-bold text-warm-white mb-1 group-hover:text-pulse-red transition-colors">
                Voice SOS Note
              </h3>
              <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                Record your cry for help in Urdu, English, or regional dialects.
              </p>
            </div>
            <div className="mt-3 flex items-center gap-1 text-xs font-bold text-pulse-red">
              <span>Record Voice Note</span>
              <ArrowIcon size={13} className="group-hover:translate-x-1 rtl:group-hover:-translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 2: Pinpoint Geolocation */}
          <div
            onClick={() => handleSOS('map')}
            className="glass glass-hover rounded-2xl p-4 sm:p-5 text-left rtl:text-right cursor-pointer group border border-white/10 relative overflow-hidden flex flex-col justify-between min-h-[150px]"
          >
            <div>
              <div className="inline-flex p-3 rounded-xl bg-sky-blue/15 text-sky-blue border border-sky-blue/30 group-hover:scale-110 transition-transform mb-3">
                <Compass size={22} />
              </div>
              <h3 className="text-sm font-bold text-warm-white mb-1 group-hover:text-sky-blue transition-colors">
                Pinpoint Location
              </h3>
              <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                Confirm GPS coordinates on interactive satellite map.
              </p>
            </div>
            <div className="mt-3 flex items-center gap-1 text-xs font-bold text-sky-blue">
              <span>Pick on Map</span>
              <ArrowIcon size={13} className="group-hover:translate-x-1 rtl:group-hover:-translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 3: Quick Text & Hazards */}
          <div
            onClick={() => handleSOS('text')}
            className="glass glass-hover rounded-2xl p-4 sm:p-5 text-left rtl:text-right cursor-pointer group border border-white/10 relative overflow-hidden flex flex-col justify-between min-h-[150px]"
          >
            <div>
              <div className="inline-flex p-3 rounded-xl bg-amber-alert/15 text-amber-alert border border-amber-alert/30 group-hover:scale-110 transition-transform mb-3">
                <Send size={22} />
              </div>
              <h3 className="text-sm font-bold text-warm-white mb-1 group-hover:text-amber-alert transition-colors">
                Quick Text Dispatch
              </h3>
              <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                Type details, stranded headcount, and medical urgencies.
              </p>
            </div>
            <div className="mt-3 flex items-center gap-1 text-xs font-bold text-amber-alert">
              <span>Type Statement</span>
              <ArrowIcon size={13} className="group-hover:translate-x-1 rtl:group-hover:-translate-x-1 transition-transform" />
            </div>
          </div>
        </div>
      </section>

      {/* Quick Incident Tracker Bar */}
      <section className="w-full glass rounded-2xl p-4 sm:p-5 mb-5 border border-white/15 shadow-xl">
        <div className="flex items-center gap-2.5 mb-2">
          <Clock className="text-sky-blue shrink-0" size={18} />
          <div>
            <h4 className="text-xs sm:text-sm font-bold text-warm-white">
              {t('quick_track_title')}
            </h4>
            <p className="text-[11px] text-slate-400">
              {t('quick_track_sub')}
            </p>
          </div>
        </div>

        <form onSubmit={handleTrackSubmit} className="flex gap-2 mt-3">
          <div className="relative flex-grow">
            <input
              id="track-code-input"
              name="track-code"
              type="text"
              value={trackCodeInput}
              onChange={(e) => setTrackCodeInput(e.target.value)}
              placeholder={t('track_placeholder')}
              className="w-full bg-slate-900/90 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-warm-white placeholder:text-slate-500 focus:outline-none focus:border-sky-blue focus:ring-1 focus:ring-sky-blue font-mono transition-all"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 rounded-xl bg-sky-blue hover:bg-sky-400 text-slate-950 font-bold text-xs transition-all flex items-center gap-1.5 shrink-0 shadow-md cursor-pointer active:scale-95"
          >
            <span>{t('track_button')}</span>
            <ArrowIcon size={14} />
          </button>
        </form>
      </section>

      {/* Instant Emergency Helplines Quick-Dial Bar */}
      <section className="w-full glass rounded-2xl p-4 mb-5 border border-white/15">
        <div className="flex items-center gap-2 mb-3">
          <Phone className="text-relief-green" size={16} />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            {t('emergency_helplines_title')}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <a
            href="tel:1122"
            className="p-2.5 rounded-xl bg-pulse-red/15 hover:bg-pulse-red/25 border border-pulse-red/30 text-pulse-red text-xs font-bold font-mono flex items-center justify-center gap-1.5 transition-all active:scale-95"
          >
            <Phone size={13} />
            <span>1122 Rescue</span>
          </a>
          <a
            href="tel:115"
            className="p-2.5 rounded-xl bg-amber-alert/15 hover:bg-amber-alert/25 border border-amber-alert/30 text-amber-alert text-xs font-bold font-mono flex items-center justify-center gap-1.5 transition-all active:scale-95"
          >
            <Phone size={13} />
            <span>115 Edhi</span>
          </a>
          <a
            href="tel:15"
            className="p-2.5 rounded-xl bg-sky-blue/15 hover:bg-sky-blue/25 border border-sky-blue/30 text-sky-blue text-xs font-bold font-mono flex items-center justify-center gap-1.5 transition-all active:scale-95"
          >
            <Phone size={13} />
            <span>15 Police</span>
          </a>
          <a
            href="tel:16"
            className="p-2.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-400 text-xs font-bold font-mono flex items-center justify-center gap-1.5 transition-all active:scale-95"
          >
            <Phone size={13} />
            <span>16 Fire</span>
          </a>
        </div>
      </section>

      {/* System Telemetry Readiness Indicators */}
      <section className="w-full glass rounded-2xl p-3.5 border border-white/10 text-center">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="p-2 rounded-xl bg-white/5 border border-white/5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">{t('gps_signal')}</span>
            <span className="text-relief-green font-bold text-xs font-mono mt-0.5 block">{t('live_active')}</span>
          </div>
          <div className="p-2 rounded-xl bg-white/5 border border-white/5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">{t('ai_verification')}</span>
            <span className="text-amber-alert font-bold text-xs font-mono mt-0.5 block">{t('ready')}</span>
          </div>
          <div className="p-2 rounded-xl bg-white/5 border border-white/5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">{t('dispatch_line')}</span>
            <span className="text-sky-blue font-bold text-xs font-mono mt-0.5 block">{t('connected')}</span>
          </div>
        </div>
      </section>
      </main>
    </div>
  );
}
