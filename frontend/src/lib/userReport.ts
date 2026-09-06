'use client';

const REPORT_CODE_KEY = 'reliefpulse_user_report_code';
const REPORT_ID_KEY = 'reliefpulse_user_report_id';
const REPORT_TIME_KEY = 'reliefpulse_user_report_time';
const REPORT_HISTORY_KEY = 'reliefpulse_user_reports_history';

export interface StoredUserReport {
  code: string;
  id?: string;
  createdAt: string;
}

export function saveUserReport(code: string, reportId?: string): void {
  if (typeof window === 'undefined') return;
  try {
    const cleanCode = code.toUpperCase().trim();
    localStorage.setItem(REPORT_CODE_KEY, cleanCode);
    if (reportId) {
      localStorage.setItem(REPORT_ID_KEY, reportId);
    }
    const timestamp = new Date().toISOString();
    localStorage.setItem(REPORT_TIME_KEY, timestamp);

    // Save to history (latest first, deduplicated)
    const historyJson = localStorage.getItem(REPORT_HISTORY_KEY);
    let history: StoredUserReport[] = [];
    if (historyJson) {
      try {
        history = JSON.parse(historyJson);
      } catch {}
    }
    history = history.filter((item) => item.code !== cleanCode);
    history.unshift({
      code: cleanCode,
      id: reportId,
      createdAt: timestamp,
    });
    localStorage.setItem(REPORT_HISTORY_KEY, JSON.stringify(history.slice(0, 10)));
  } catch (err) {
    console.warn('[userReport] Failed to save report to localStorage:', err);
  }
}

export function getUserReportCode(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const code = localStorage.getItem(REPORT_CODE_KEY);
    if (code && code.trim().length > 0) {
      return code.trim().toUpperCase();
    }
    // Check history
    const historyJson = localStorage.getItem(REPORT_HISTORY_KEY);
    if (historyJson) {
      const history = JSON.parse(historyJson);
      if (history && history.length > 0 && history[0].code) {
        return history[0].code.trim().toUpperCase();
      }
    }
    return null;
  } catch {
    return null;
  }
}

export function getUserReportId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(REPORT_ID_KEY);
  } catch {
    return null;
  }
}

export function getUserReportsHistory(): StoredUserReport[] {
  if (typeof window === 'undefined') return [];
  try {
    const historyJson = localStorage.getItem(REPORT_HISTORY_KEY);
    if (historyJson) {
      return JSON.parse(historyJson);
    }
    const currentCode = getUserReportCode();
    if (currentCode) {
      return [{ code: currentCode, id: getUserReportId() || undefined, createdAt: new Date().toISOString() }];
    }
    return [];
  } catch {
    return [];
  }
}

export function clearUserReport(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(REPORT_CODE_KEY);
    localStorage.removeItem(REPORT_ID_KEY);
    localStorage.removeItem(REPORT_TIME_KEY);
    localStorage.removeItem(REPORT_HISTORY_KEY);
  } catch (err) {
    console.warn('[userReport] Failed to clear report:', err);
  }
}
