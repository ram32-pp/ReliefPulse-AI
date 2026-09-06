'use client';

import React from 'react';
import { useTranslation, Locale } from '@/lib/i18n';
import { Globe } from 'lucide-react';

interface LanguageSwitcherProps {
  className?: string;
  compact?: boolean;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className = '', compact = false }) => {
  const { locale, setLocale } = useTranslation();

  // User specification:
  // - English: "English"
  // - Urdu Arabic Script: "اُردُو (عربی)" / "اُردُو" in authentic Arabic transcript with diacritics
  // - Urdu Roman Script: "Urdu (Roman)" / "Urdu" (NEVER just "Roman")
  const options: { id: Locale; fullLabel: string; compactLabel: string; tooltip: string }[] = [
    {
      id: 'en',
      fullLabel: 'English',
      compactLabel: 'English',
      tooltip: 'Switch to English',
    },
    {
      id: 'urdu_script',
      fullLabel: 'اُردُو (عربی)',
      compactLabel: 'اُردُو',
      tooltip: 'اُردُو (عربی رسم الخط - Nastaliq Script)',
    },
    {
      id: 'roman_urdu',
      fullLabel: 'Urdu (Roman)',
      compactLabel: 'Urdu',
      tooltip: 'Urdu in Roman / Latin Script',
    },
  ];

  return (
    <div
      suppressHydrationWarning
      className={`inline-flex items-center p-1 rounded-xl bg-slate-950/80 border border-white/15 backdrop-blur-xl shadow-lg shrink-0 ${className}`}
      role="group"
      aria-label="Language selection"
    >
      <div className="hidden sm:flex items-center px-1.5 text-slate-400 shrink-0">
        <Globe size={13} className="text-sky-blue/80" />
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {options.map((opt) => {
          const isActive = locale === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => setLocale(opt.id)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 active:scale-95 flex items-center justify-center cursor-pointer shrink-0 ${
                isActive
                  ? 'bg-gradient-to-r from-sky-blue/30 to-emerald-400/20 text-sky-blue border border-sky-blue/50 shadow-[0_0_15px_rgba(0,176,255,0.35)]'
                  : 'text-slate-400 hover:text-warm-white hover:bg-white/5 border border-transparent'
              }`}
              title={opt.tooltip}
              aria-pressed={isActive}
            >
              <span className={compact ? 'inline' : 'inline md:hidden'}>
                {opt.compactLabel}
              </span>
              <span className={compact ? 'hidden' : 'hidden md:inline'}>
                {opt.fullLabel}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default LanguageSwitcher;
