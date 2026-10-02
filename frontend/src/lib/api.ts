import { API_BASE_URL } from './constants';

export const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = {
    ...options.headers,
  };

  if (!(options.body instanceof FormData)) {
    (headers as any)['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText} (${response.status})`);
  }

  return response.json();
};

export const uploadReport = async (data: FormData | any) => {
  if (data instanceof FormData) {
    return apiFetch('/reports/multipart', {
      method: 'POST',
      body: data,
    });
  }

  return apiFetch('/reports', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const fetchReportStatus = async (codeOrId: string) => {
  try {
    return await apiFetch(`/reports/code/${encodeURIComponent(codeOrId)}/status`);
  } catch (err) {
    // Fallback to report ID lookup if valid UUID
    return await apiFetch(`/reports/${encodeURIComponent(codeOrId)}/status`);
  }
};

export const advanceReliefStatus = async (params: {
  reportId?: string;
  incidentId?: string;
  reliefStatus: string;
  teamName?: string;
  etaMinutes?: number;
}) => {
  return apiFetch('/coordinator/advance-relief', {
    method: 'POST',
    body: JSON.stringify({
      report_id: params.reportId,
      incident_id: params.incidentId,
      relief_status: params.reliefStatus,
      relief_team_name: params.teamName,
      rescue_eta_minutes: params.etaMinutes,
    }),
  });
};

export interface CaptureNonceResponse {
  nonce: string;
  expires_at: string;
  ttl_seconds: number;
}

export const fetchCaptureNonce = async (): Promise<CaptureNonceResponse> => {
  return apiFetch('/auth/capture-nonce');
};

export interface TriageQueueParams {
  severity?: string;
  status?: string;
  triage_tier?: string;
  page?: number;
  per_page?: number;
}

export const fetchTriageQueue = async (params?: TriageQueueParams) => {
  const query = new URLSearchParams();
  if (params?.severity) query.append('severity', params.severity);
  if (params?.status) query.append('status', params.status);
  if (params?.triage_tier) query.append('triage_tier', params.triage_tier);
  if (params?.page) query.append('page', params.page.toString());
  if (params?.per_page) query.append('per_page', params.per_page.toString());
  const queryString = query.toString();
  return apiFetch(`/coordinator/triage${queryString ? `?${queryString}` : ''}`);
};

export const fetchIncidentDetail = async (incidentId: string) => {
  return apiFetch(`/coordinator/incidents/${encodeURIComponent(incidentId)}`);
};

export const triggerRapidCallback = async (params: {
  reportId?: string;
  incidentId?: string;
  phoneNumber?: string;
  channel?: 'sms' | 'ivr' | 'auto';
}) => {
  return apiFetch('/coordinator/trigger-callback', {
    method: 'POST',
    body: JSON.stringify({
      report_id: params.reportId,
      incident_id: params.incidentId,
      phone_number: params.phoneNumber,
      channel: params.channel || 'auto',
    }),
  });
};

export const rejectIncident = async (params: { incidentId: string; reason?: string; notes?: string }) => {
  return apiFetch('/coordinator/reject', {
    method: 'POST',
    body: JSON.stringify({
      incident_id: params.incidentId,
      action: 'reject',
      reason: params.reason || 'False alarm or duplicate signal',
      notes: params.notes,
    }),
  });
};


