'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n';
import { STATUS_CODES } from '@/lib/constants';
import { CheckCircle2, Clock, Circle } from 'lucide-react';

interface StatusTimelineProps {
  status: string;
}

export const StatusTimeline: React.FC<StatusTimelineProps> = ({ status }) => {
  const { t } = useTranslation();

  const steps = [
    { key: STATUS_CODES.PENDING, label: t('sent') || 'Signal Received' },
    { key: STATUS_CODES.VERIFIED, label: t('ai_verified') || 'AI Verified & Triaged' },
    { key: STATUS_CODES.DISPATCHED, label: t('team_coming') || 'Rescue Team Dispatched' },
    { key: STATUS_CODES.RESOLVED, label: t('help_received') || 'On-Scene Relief Active' },
  ];

  const currentIndex = steps.findIndex((s) => s.key === status);
  const activeIndex = currentIndex < 0 ? 1 : currentIndex;

  return (
    <div className="flex flex-col gap-6 py-2 px-4 border-l-2 rtl:border-l-0 rtl:border-r-2 border-white/15 ml-4 rtl:ml-0 rtl:mr-4 relative">
      {steps.map((step, index) => {
        const isPast = index < activeIndex;
        const isCurrent = index === activeIndex;

        return (
          <div key={step.key} className="flex items-center gap-4 relative">
            <div className="absolute -left-[27px] rtl:-right-[27px] rtl:left-auto bg-[#090f20] p-1 rounded-full border border-white/10">
              {isPast ? (
                <CheckCircle2 className="text-relief-green" size={22} />
              ) : isCurrent ? (
                <Clock className="text-amber-alert animate-pulse" size={22} />
              ) : (
                <Circle className="text-slate-600" size={22} />
              )}
            </div>

            <div className="ml-3 rtl:mr-3 rtl:ml-0">
              <span
                className={`text-sm font-bold block ${
                  isPast
                    ? 'text-relief-green'
                    : isCurrent
                    ? 'text-amber-alert'
                    : 'text-slate-500'
                }`}
              >
                {step.label}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {isPast ? 'Completed' : isCurrent ? 'In Progress' : 'Pending'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
