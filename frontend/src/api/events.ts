import { apiRequest } from './client';

export interface PaymentFailedEventResponse {
  event_id: string;
  event_type: string;
  payment_id: number;
  status: string;
  recovery_result: {
    payment_id: number;
    decision: 'retry_payment' | 'create_payment_link' | 'send_recovery_message' | 'escalate' | 'stop';
    reason: string;
    final_status: 'success' | 'in_progress' | 'escalated' | 'stopped';
    amount_recovered_paise: number;
    actions: Array<{
      tool?: string;
      action_type?: string;
      status?: string;
      result?: string;
      amount_recovered_paise?: number;
    }>;
  };
}

export async function triggerPaymentFailed(
  paymentId: number,
  eventId?: string
): Promise<PaymentFailedEventResponse> {
  const generatedEventId = eventId || `evt_ui_${Math.random().toString(36).substring(2, 10)}`;
  return apiRequest<PaymentFailedEventResponse>('/api/events/payment-failed', {
    method: 'POST',
    body: JSON.stringify({
      event_type: 'payment.failed',
      payment_id: paymentId,
      event_id: generatedEventId,
    }),
  });
}

export async function triggerAgentRecovery(paymentId: number): Promise<any> {
  return apiRequest<any>(`/api/agent/recover/${paymentId}`, {
    method: 'POST',
  });
}

export async function simulatePaymentCompletion(paymentId: number): Promise<any> {
  return apiRequest<any>(`/api/events/complete-payment-link/${paymentId}`, {
    method: 'POST',
  });
}
