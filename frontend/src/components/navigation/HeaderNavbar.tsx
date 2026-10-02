'use client';

import React, { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useTranslation } from '@/lib/i18n';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { getUserReportCode } from '@/lib/userReport';
import {
  Home,
  Radio,
  Clock,
  Phone,
  Menu,
  X,
  ChevronRight,
} from 'lucide-react';

interface HeaderNavbarProps {
  className?: string;
}

export const HeaderNavbar: React.FC<HeaderNavbarProps> = ({ className = '' }) => {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useTranslation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { label: t('nav_home') || 'Home', path: '/', icon: Home },
    { label: t('nav_sos') || 'Emergency SOS', path: '/sos', icon: Radio, highlight: true },
    { label: t('nav_track') || 'Live Tracking', path: '/status', icon: Clock },
  ];

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  };

  const handleNavClick = (path: string) => {
    setMobileMenuOpen(false);
    if (path === '/status') {
      const userCode = getUserReportCode();
      if (userCode) {
        router.push(`/status/${userCode}`);
        return;
      }
    }
    router.push(path);
  };

  return (
    <header suppressHydrationWarning className={`w-full sticky top-3 z-50 transition-all duration-300 ${className}`}>
      <div suppressHydrationWarning className="glass rounded-2xl border border-white/15 px-3 sm:px-4 py-2.5 shadow-2xl backdrop-blur-2xl flex items-center justify-between gap-2 sm:gap-4 overflow-hidden">
        {/* Brand Logo & Redesigned Application Name */}
        <div
          onClick={() => router.push('/')}
          className="flex items-center gap-2.5 sm:gap-3 cursor-pointer group shrink-0"
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

        {/* Desktop Navigation Links */}
        <nav className="hidden sm:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 shrink-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <button
                key={item.path}
                type="button"
                onClick={() => handleNavClick(item.path)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
                  active
                    ? item.highlight
                      ? 'bg-pulse-red text-white shadow-lg'
                      : 'bg-sky-blue/20 text-sky-blue border border-sky-blue/30'
                    : 'text-slate-300 hover:text-white hover:bg-white/10'
                }`}
              >
                <Icon size={14} className={item.highlight && !active ? 'text-pulse-red' : ''} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Action Controls: 1122 Helpline + Language Switcher + Mobile Toggle */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Emergency Ambulance 1122 Button */}
          <a
            href="tel:1122"
            title="Call Emergency Rescue 1122"
            className="flex items-center gap-1 sm:gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl bg-gradient-to-r from-pulse-red to-rose-600 hover:from-red-600 hover:to-rose-700 text-white text-[11px] sm:text-xs font-black font-mono tabular-nums shadow-md border border-red-400/40 transition-all active:scale-95 shrink-0 cursor-pointer"
          >
            <span className="text-xs">🚑</span>
            <span className="tracking-wide">1122</span>
            <span className="hidden xl:inline text-[10px] font-sans font-bold uppercase opacity-90">Rescue</span>
          </a>

          {/* Segmented Language Switcher */}
          <div className="shrink-0">
            <LanguageSwitcher compact={true} />
          </div>

          {/* Mobile Menu Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="sm:hidden p-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 border border-white/10 cursor-pointer shrink-0"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden mt-2 p-3 glass-panel rounded-2xl border border-white/15 shadow-2xl backdrop-blur-2xl animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <button
                  key={item.path}
                  type="button"
                  onClick={() => handleNavClick(item.path)}
                  className={`w-full px-3 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between cursor-pointer ${
                    active
                      ? 'bg-sky-blue/20 text-sky-blue border border-sky-blue/30'
                      : 'text-slate-300 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon size={16} className={item.highlight ? 'text-pulse-red' : ''} />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight size={14} className="text-slate-500 rtl:rotate-180" />
                </button>
              );
            })}
          </div>

          <div className="h-px w-full bg-white/10 my-2.5" />

          {/* Emergency Helplines Direct Dialers */}
          <div className="grid grid-cols-2 gap-2 text-center">
            <a
              href="tel:1122"
              className="py-2.5 px-3 rounded-xl bg-pulse-red text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-lg active:scale-95 cursor-pointer font-mono"
            >
              <Phone size={13} /> 1122 Rescue
            </a>
            <a
              href="tel:115"
              className="py-2.5 px-3 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1.5 border border-white/10 active:scale-95 cursor-pointer font-mono"
            >
              <Phone size={13} /> 115 Edhi
            </a>
          </div>
        </div>
      )}
    </header>
  );
};

export default HeaderNavbar;
