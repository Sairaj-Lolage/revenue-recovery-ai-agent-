import { apiRequest } from './client';
import type { Customer } from '../types';

export async function fetchCustomers(): Promise<Customer[]> {
  return apiRequest<Customer[]>('/api/customers');
}

export async function fetchCustomer(customerId: number): Promise<Customer> {
  return apiRequest<Customer>(`/api/customers/${customerId}`);
}
