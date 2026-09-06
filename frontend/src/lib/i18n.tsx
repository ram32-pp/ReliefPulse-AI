'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { en, TranslationKey } from './translations/en';
import { roman_urdu } from './translations/roman_urdu';
import { urdu } from './translations/urdu';

export type Locale = 'en' | 'urdu_script' | 'roman_urdu';

interface TranslationMap {
  [key: string]: string;
}

const translations: Record<Locale, TranslationMap> = {
  en,
  roman_urdu,
  urdu_script: urdu,
};

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey) => string;
  dir: 'ltr' | 'rtl';
  isRTL: boolean;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export const I18nProvider = ({ children }: { children: ReactNode }) => {
  const [locale, setLocale] = useState<Locale>('en');

  useEffect(() => {
    try {
      const saved = localStorage.getItem('locale') as Locale;
      if (saved && translations[saved]) {
        setLocale(saved);
      }
    } catch {
      // localStorage may fail in private mode
    }
  }, []);

  const dir = locale === 'urdu_script' ? 'rtl' : 'ltr';

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dir = dir;
      if (locale === 'urdu_script') {
        document.documentElement.lang = 'ur';
        document.body.classList.add('urdu-mode');
      } else if (locale === 'roman_urdu') {
        document.documentElement.lang = 'ur-Latn';
        document.body.classList.remove('urdu-mode');
      } else {
        document.documentElement.lang = 'en';
        document.body.classList.remove('urdu-mode');
      }
    }
  }, [locale, dir]);

  const changeLocale = (newLocale: Locale) => {
    setLocale(newLocale);
    try {
      localStorage.setItem('locale', newLocale);
    } catch {
      // ignore
    }
  };

  const t = (key: TranslationKey): string => {
    return (translations[locale] as any)?.[key] || translations['en']?.[key] || key;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale: changeLocale, t, dir, isRTL: dir === 'rtl' }}>
      <div
        dir={dir}
        className={locale === 'urdu_script' ? 'urdu-mode' : ''}
        suppressHydrationWarning
      >
        {children}
      </div>
    </I18nContext.Provider>
  );
};

export const useTranslation = () => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within an I18nProvider');
  }
  return context;
};
