'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  addToQueue,
  getQueue,
  removeFromQueue,
  updateQueueItem,
  clearQueue as dbClearQueue,
  OfflineQueueItem,
} from '@/lib/offline-db';
import { API_BASE_URL } from '@/lib/constants';
import { saveUserReport } from '@/lib/userReport';

export const useOfflineQueue = () => {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && typeof navigator !== 'undefined') {
      return navigator.onLine ?? true;
    }
    return true;
  });
  const [queueCount, setQueueCount] = useState<number>(0);
  const [queuedItems, setQueuedItems] = useState<OfflineQueueItem[]>([]);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSyncedCode, setLastSyncedCode] = useState<string | null>(null);
  const isSyncingRef = useRef(false);

  const checkQueue = useCallback(async () => {
    try {
      const queue = await getQueue();
      setQueuedItems(queue);
      setQueueCount(queue.length);
    } catch {
      setQueuedItems([]);
      setQueueCount(0);
    }
  }, []);

  const resolveTargetUrl = (storedUrl: string): string => {
    try {
      if (storedUrl.includes('/reports')) {
        return `${API_BASE_URL}/reports`;
      }
      if (storedUrl.startsWith('http')) {
        const parsed = new URL(storedUrl);
        return `${API_BASE_URL}${parsed.pathname}`;
      }
      return `${API_BASE_URL}${storedUrl.startsWith('/') ? storedUrl : `/${storedUrl}`}`;
    } catch {
      return storedUrl;
    }
  };

  /**
   * Sequential auto-retry synchronization loop.
   * Sends requests one by one, only purging IndexedDB item upon receiving HTTP 200/201.
   */
  const syncQueue = useCallback(async () => {
    if (isSyncingRef.current || !navigator.onLine) return;
    isSyncingRef.current = true;
    setIsSyncing(true);

    try {
      const queue = await getQueue();
      if (queue.length === 0) return;

      for (const item of queue) {
        if (!navigator.onLine) {
          console.warn('[OfflineQueue] Device lost connectivity during sync; pausing queue.');
          break;
        }

        try {
          await updateQueueItem({ ...item, sync_status: 'syncing' });

          const targetUrl = resolveTargetUrl(item.url);
          const body =
            typeof item.body === 'object' && !item.isFormData && !(item.body instanceof FormData)
              ? JSON.stringify(item.body)
              : item.body;

          const response = await fetch(targetUrl, {
            method: item.method || 'POST',
            headers: item.headers || (item.isFormData ? undefined : { 'Content-Type': 'application/json' }),
            body,
          });

          // Only purge entry upon receiving HTTP 200 OK or 201 Created
          if (response.status === 200 || response.status === 201) {
            try {
              const data = await response.json();
              const assignedCode = data?.display_code || (data?.report_id ? `RP-${data.report_id.slice(0, 4).toUpperCase()}` : null);
              if (assignedCode) {
                saveUserReport(assignedCode, data.report_id);
                setLastSyncedCode(assignedCode);
              }
            } catch (jsonErr) {
              console.warn('[OfflineQueue] Response parsing warning:', jsonErr);
            }
            await removeFromQueue(item.id);
          } else if (response.status >= 400 && response.status < 500 && response.status !== 408 && response.status !== 429) {
            // Unrecoverable client error: discard so queue is not permanently wedged
            console.warn(`[OfflineQueue] Item ${item.id} rejected with client error HTTP ${response.status}. Removing.`);
            await removeFromQueue(item.id);
          } else {
            // Transient 5xx or server rate limit: increment retry, remain queued
            const retries = (item.retryCount || 0) + 1;
            await updateQueueItem({ ...item, retryCount: retries, sync_status: 'queued' });
            break; // Pause loop to wait for server recovery
          }
        } catch (networkErr) {
          console.warn(`[OfflineQueue] Sync paused for item ${item.id} (network unreachable):`, networkErr);
          const retries = (item.retryCount || 0) + 1;
          await updateQueueItem({ ...item, retryCount: retries, sync_status: 'queued' });
          break; // Stop sequential loop if network dropped
        }
      }
    } finally {
      await checkQueue();
      isSyncingRef.current = false;
      setIsSyncing(false);
    }
  }, [checkQueue]);

  // Attach native window 'online' and 'offline' listeners
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      setIsOnline(true);
      syncQueue();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    checkQueue();

    // Trigger initial sync if online
    if (navigator.onLine) {
      syncQueue();
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [syncQueue, checkQueue]);

  const enqueueRequest = async (
    url: string,
    method: string,
    data: any,
    isFormData = false,
    reportCode?: string
  ) => {
    const id = `queued_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const newItem: OfflineQueueItem = {
      id,
      url,
      method,
      body: data,
      isFormData,
      timestamp: Date.now(),
      retryCount: 0,
      sync_status: 'queued',
      reportCode,
    };
    await addToQueue(newItem);
    await checkQueue();
    return id;
  };

  const clearAllQueue = async () => {
    await dbClearQueue();
    await checkQueue();
  };

  return {
    isOnline,
    queueCount,
    queuedItems,
    isSyncing,
    lastSyncedCode,
    enqueueRequest,
    syncQueue,
    clearQueue: clearAllQueue,
  };
};
