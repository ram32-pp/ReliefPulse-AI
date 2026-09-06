'use client';

import React, { useState, useEffect } from 'react';
import { WifiOff, RefreshCw, CheckCircle2, ShieldCheck } from 'lucide-react';
import { useOfflineQueue } from '@/hooks/useOfflineQueue';

export const OfflineSyncBanner: React.FC = () => {
  const [isMounted, setIsMounted] = useState(false);
  const { isOnline, queueCount, isSyncing, syncQueue } = useOfflineQueue();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Guarantee matching SSR and initial client hydration by returning null before mount
  if (!isMounted) {
    return null;
  }

  // If online and no items pending, render nothing
  if (isOnline && queueCount === 0 && !isSyncing) {
    return null;
  }

  return (
    <aside
      aria-label="Offline Sync Banner"
      className="w-full bg-gradient-to-r from-amber-600/90 to-orange-700/90 text-white px-4 py-2.5 shadow-lg border-b border-white/20 transition-all z-[100]"
    >
      <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          {!isOnline ? (
            <div className="p-1.5 rounded-lg bg-black/25 text-amber-200">
              <WifiOff size={16} className="animate-pulse" />
            </div>
          ) : isSyncing ? (
            <div className="p-1.5 rounded-lg bg-black/25 text-white">
              <RefreshCw size={16} className="animate-spin" />
            </div>
          ) : (
            <div className="p-1.5 rounded-lg bg-black/25 text-emerald-200">
              <ShieldCheck size={16} />
            </div>
          )}

          <div>
            {!isOnline ? (
              <div>
                <span className="font-black uppercase tracking-wider block">
                  Offline Resilience Active ({queueCount} Report{queueCount !== 1 ? 's' : ''} Saved Locally)
                </span>
                <span className="text-amber-100 text-[11px]">
                  Your emergency report is safely secured in browser IndexedDB. It will automatically transmit to rescue coordinators the moment network connectivity returns.
                </span>
              </div>
            ) : isSyncing ? (
              <div>
                <span className="font-black uppercase tracking-wider block">
                  Network Reconnected &bull; Transmitting Reports...
                </span>
                <span className="text-amber-100 text-[11px]">
                  Sequentially syncing locally queued emergency payloads to the command center.
                </span>
              </div>
            ) : (
              <div>
                <span className="font-black uppercase tracking-wider block">
                  {queueCount} Pending Offline Emergency Report{queueCount !== 1 ? 's' : ''}
                </span>
                <span className="text-amber-100 text-[11px]">
                  Device connected. Synchronizing queued distress signals with live rescue triage.
                </span>
              </div>
            )}
          </div>
        </div>

        {isOnline && queueCount > 0 && !isSyncing && (
          <button
            type="button"
            onClick={() => syncQueue()}
            className="px-3 py-1.5 rounded-xl bg-white text-slate-950 font-black text-xs hover:bg-amber-100 active:scale-95 transition-all shadow cursor-pointer flex items-center gap-1.5 shrink-0"
          >
            <RefreshCw size={13} />
            <span>Transmit Now</span>
          </button>
        )}
      </div>
    </aside>
  );
};

export default OfflineSyncBanner;
