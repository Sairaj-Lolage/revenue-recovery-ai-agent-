export type PaymentStatus = 'pending' | 'success' | 'failed';

export type CaseStatus = 'OPEN' | 'IN_PROGRESS' | 'RECOVERED' | 'ESCALATED' | 'STOPPED';

export type ActionType = 
  | 'retry_payment'
  | 'create_payment_link'
  | 'send_recovery_message'
  | 'escalate'
  | 'stop';

export type AuditActor = 'agent' | 'system' | 'guardrail' | 'tool';

export type EventType =
  | 'CASE_CREATED'
  | 'RISK_DETECTED'
  | 'DIAGNOSIS_COMPLETED'
  | 'ACTION_PROPOSED'
  | 'GUARDRAIL_CHECKED'
  | 'ACTION_EXECUTED'
  | 'PAYMENT_RECOVERED'
  | 'ESCALATED'
  | 'WORKFLOW_STOPPED';

export interface Customer {
  id: number;
  name: string;
  email: string;
  phone?: string;
  segment: 'Starter' | 'Pro' | 'Enterprise' | 'VIP' | string;
  total_paid_paise: number;
  successful_payments: number;
  failed_payments: number;
  recovery_cases_count?: number;
  opted_out: boolean;
  created_at: string;
}

export interface Payment {
  id: number;
  customer_id: number;
  customer_name?: string;
  customer_email?: string;
  amount_paise: number;
  currency: string;
  status: PaymentStatus;
  failure_reason?: string;
  attempt_count: number;
  recovery_scenario?: 'EASY_RECOVERY' | 'PAYMENT_LINK_RECOVERY' | 'REPEATED_FAILURE' | 'HIGH_VALUE' | 'OPTED_OUT' | 'UNRECOVERABLE';
  created_at: string;
  updated_at: string;
  case_id?: number;
  case_status?: CaseStatus;
  recovery_case_id?: number;
  recovery_status?: CaseStatus;
  last_action?: string;
}

export interface RecoveryAction {
  id: number;
  recovery_case_id: number;
  action_type: ActionType;
  reason?: string;
  approved: boolean;
  result?: string;
  amount_recovered_paise: number;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  title: string;
  description: string;
  type: 'agent' | 'guardrail' | 'tool' | 'customer' | 'system';
  timestamp: string;
  status?: 'success' | 'failed' | 'warning' | 'info';
}

export interface AIDecision {
  proposed_action: ActionType;
  why: string;
  policy_decision: 'Approved' | 'Blocked';
  policy_reason?: string;
  execution_result: string;
  recovered_amount_paise: number;
}

export interface RecoveryCase {
  id: number;
  payment_id: number;
  customer_id: number;
  customer_name?: string;
  customer_email?: string;
  customer_opted_out?: boolean;
  amount_at_risk_paise: number;
  amount_recovered_paise: number;
  risk_score?: number; // 0-100
  status: CaseStatus;
  current_step?: string;
  attempt_count: number;
  failure_reason?: string;
  scenario?: string;
  created_at: string;
  updated_at?: string;
  ai_decision?: AIDecision;
  decision_reasoning?: {
    proposed_action?: string;
    reason?: string;
    policy_result?: string;
    guardrail_note?: string;
  };
  actions: RecoveryAction[];
  timeline?: TimelineEvent[];
  audit_logs?: AuditLog[];
  next_step?: string;
}

export interface AuditLog {
  id: number;
  recovery_case_id: number;
  payment_id?: number;
  event_type: EventType | string;
  actor: AuditActor;
  details: string;
  timestamp: string;
}

export interface DashboardKPIS {
  amountAtRiskPaise: number;
  failedCount: number;
  recoveredAmountPaise: number;
  recoveryRatePercent: number;
  inProgressCount: number;
  escalatedCount: number;
  stoppedCount: number;
  totalRecoveriesToday: number;
}
