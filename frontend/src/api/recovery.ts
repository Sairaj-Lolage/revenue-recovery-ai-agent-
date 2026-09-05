import { apiRequest } from './client';
import type { RecoveryCase, DashboardKPIS } from '../types';

export async function fetchRecoveryCases(): Promise<RecoveryCase[]> {
  return apiRequest<RecoveryCase[]>('/api/recovery-cases');
}

export async function fetchRecoveryCase(caseId: number): Promise<RecoveryCase> {
  return apiRequest<RecoveryCase>(`/api/recovery-cases/${caseId}`);
}

export async function fetchDashboardStats(): Promise<DashboardKPIS> {
  return apiRequest<DashboardKPIS>('/api/dashboard/stats');
}
