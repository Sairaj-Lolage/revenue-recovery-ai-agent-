import { apiRequest } from './client';
import type { AuditLog } from '../types';

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return apiRequest<AuditLog[]>('/api/audit-logs');
}
