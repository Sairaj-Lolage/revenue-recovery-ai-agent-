import { apiRequest } from './client';

export interface PolicySettings {
  max_retry_attempts: number;
  high_value_threshold_paise: number;
  strict_opt_out: boolean;
  auto_escalate_delay_hours: number | null;
}

export function fetchPolicySettings(): Promise<PolicySettings> {
  return apiRequest<PolicySettings>('/api/settings/policy');
}

export function updatePolicySettings(settings: Pick<PolicySettings, 'max_retry_attempts' | 'high_value_threshold_paise'>): Promise<PolicySettings> {
  return apiRequest<PolicySettings>('/api/settings/policy', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}
