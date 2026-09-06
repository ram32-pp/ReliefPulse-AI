'use client';

import { useEffect } from 'react';

export function ServiceWorkerCleaner() {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      // In development or when recovering from stale chunk errors, ensure no rogue service worker intercepts chunks
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        for (const registration of registrations) {
          console.warn('[PWA] Clearing service worker to prevent chunk loading collisions:', registration.scope);
          registration.unregister();
        }
      });
      if ('caches' in window) {
        caches.keys().then((keys) => {
          for (const key of keys) {
            caches.delete(key);
          }
        });
      }
    }
  }, []);

  return null;
}
