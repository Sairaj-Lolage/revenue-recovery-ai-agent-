import { apiRequest } from './client';
import type { Payment } from '../types';

export async function fetchPayments(): Promise<Payment[]> {
  return apiRequest<Payment[]>('/api/payments');
}

export async function fetchPayment(paymentId: number): Promise<Payment> {
  return apiRequest<Payment>(`/api/payments/${paymentId}`);
}
