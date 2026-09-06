'use client';

import React from 'react';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { useOfflineQueue } from '@/hooks/useOfflineQueue';
import { useTranslation } from '@/lib/i18n';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

export const OfflineBadge: React.FC = () => {
  const isOnline = useOnlineStatus();
  const { queueCount, syncQueue, isSyncing } = useOfflineQueue();
  const { t } = useTranslation();

  if (isOnline && queueCount === 0) {
    return (
      <div suppressHydrationWarning className="flex items-center gap-2 text-relief-green text-sm font-medium">
        <Wifi size={16} />
        <span>{t('online')}</span>
      </div>
    );
  }

  if (isOnline && queueCount > 0) {
    return (
      <button
        suppressHydrationWarning
        onClick={() => syncQueue()}
        className="flex items-center gap-2 text-sky-blue text-sm font-medium hover:underline cursor-pointer"
        title="Click to trigger sync"
      >
        <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} />
        <span>{isSyncing ? t('syncing') : 'Pending'}: {queueCount}</span>
      </button>
    );
  }


  return (
    <div suppressHydrationWarning className="flex items-center gap-2 text-slate-grey text-sm font-medium">
      <WifiOff size={16} />
      <span>{t('offline')}</span>
    </div>
  );
};
