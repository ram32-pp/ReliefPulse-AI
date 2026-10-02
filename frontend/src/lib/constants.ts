export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:5000';

export const HAZARD_TYPES = {
  FLOOD: 'flood',
  COLLAPSE: 'structural_collapse',
  INJURED: 'medical_emergency',
  CHILDREN: 'vulnerable_children',
  FIRE: 'fire',
  NO_FOOD: 'supply_shortage',
};

export const SEVERITY_LEVELS = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

export const STATUS_CODES = {
  PENDING: 'pending',
  VERIFIED: 'verified',
  DISPATCHED: 'dispatched',
  RESOLVED: 'resolved',
};
