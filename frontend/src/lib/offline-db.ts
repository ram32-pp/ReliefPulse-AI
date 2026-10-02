import type { DBSchema, IDBPDatabase } from 'idb';

export type SyncStatus = 'queued' | 'syncing' | 'synced' | 'failed';

export interface OfflineQueueItem {
  id: string;
  url: string;
  method: string;
  headers?: Record<string, string>;
  body: any; // Serialized JSON or structured payload
  isFormData: boolean;
  timestamp: number;
  retryCount?: number;
  sync_status: SyncStatus;
  reportCode?: string;
}

interface ReliefPulseDB extends DBSchema {
  offlineQueue: {
    key: string;
    value: OfflineQueueItem;
  };
}

let dbPromise: Promise<IDBPDatabase<ReliefPulseDB>> | null = null;

const getDB = async (): Promise<IDBPDatabase<ReliefPulseDB> | null> => {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') return null;
  if (!dbPromise) {
    try {
      const { openDB } = await import('idb');
      dbPromise = openDB<ReliefPulseDB>('ReliefPulseDB', 2, {
        upgrade(db) {
          if (!db.objectStoreNames.contains('offlineQueue')) {
            db.createObjectStore('offlineQueue', { keyPath: 'id' });
          }
        },
      });
    } catch (err) {
      console.warn('[offline-db] Failed to initialize IndexedDB:', err);
      return null;
    }
  }
  return dbPromise;
};

export const addToQueue = async (requestData: Omit<OfflineQueueItem, 'sync_status'> & { sync_status?: SyncStatus }) => {
  const db = await getDB();
  if (!db) return;
  const item: OfflineQueueItem = {
    ...requestData,
    sync_status: requestData.sync_status || 'queued',
  };
  await db.put('offlineQueue', item);
  return item;
};

export const getQueue = async (): Promise<OfflineQueueItem[]> => {
  const db = await getDB();
  if (!db) return [];
  return db.getAll('offlineQueue');
};

export const removeFromQueue = async (id: string) => {
  const db = await getDB();
  if (!db) return;
  await db.delete('offlineQueue', id);
};

export const updateQueueItem = async (requestData: OfflineQueueItem) => {
  const db = await getDB();
  if (!db) return;
  await db.put('offlineQueue', requestData);
};

export const clearQueue = async () => {
  const db = await getDB();
  if (!db) return;
  await db.clear('offlineQueue');
};
