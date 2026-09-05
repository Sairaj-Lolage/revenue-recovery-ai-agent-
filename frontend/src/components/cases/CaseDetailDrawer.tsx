import React, { useEffect, useState } from 'react';
import { X, ShieldAlert, ArrowRight, User, RefreshCw, CheckCircle, Ban, AlertTriangle } from 'lucide-react';
import type { RecoveryCase, TimelineEvent, AuditLog, ActionType } from '../../types';
import { fetchRecoveryCase, simulatePaymentCompletion, triggerPaymentFailed } from '../../api';
import { formatINR, formatTimestamp } from '../../utils/formatters';
import { Badge } from '../common/Badge';
import { AIDecisionCard } from './AIDecisionCard';
import { TimelineStepper } from './TimelineStepper';

interface CaseDetailDrawerProps {
  caseId: number | null;
  onClose: () => void;
  onRefreshData?: () => void;
  onShowToast?: (message: string, type?: 'success' | 'info' | 'warning') => void;
}

export const CaseDetailDrawer: React.FC<CaseDetailDrawerProps> = ({
  caseId,
  onClose,
  onRefreshData,
  onShowToast,
}) => {
  const [caseDetail, setCaseDetail] = useState<RecoveryCase | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!caseId) {
      setCaseDetail(null);
      return;
    }

    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchRecoveryCase(caseId);
        setCaseDetail(data);
      } catch (err: any) {
        console.error('Failed to load recovery case detail:', err);
        setError(err.message || 'Failed to load case details from backend');
      } finally {
        setLoading(false);
      }
    };

    loadDetail();
  }, [caseId]);

  if (!caseId) return null;

  const handleSimulatePaymentCompletion = async () => {
    if (!caseDetail) return;
    setActionLoading(true);
    try {
      if (onShowToast) onShowToast(`Simulating customer payment link completion for Payment #${caseDetail.payment_id}...`, 'info');
      const res = await simulatePaymentCompletion(caseDetail.payment_id);
      
      // Also run agent follow-up to update state
      await triggerPaymentFailed(caseDetail.payment_id);

      if (res.success) {
        if (onShowToast) onShowToast(`Payment completed! ${formatINR(res.amount_recovered_paise)} recovered.`, 'success');
      } else {
        if (onShowToast) onShowToast(`Payment completion attempt: ${res.message}`, 'warning');
      }

      // Reload detail
      const refreshed = await fetchRecoveryCase(caseId);
      setCaseDetail(refreshed);
      if (onRefreshData) onRefreshData();
    } catch (err: any) {
      if (onShowToast) onShowToast(`Simulation error: ${err.message}`, 'warning');
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerRecovery = async () => {
    if (!caseDetail) return;
    setActionLoading(true);
    try {
      if (onShowToast) onShowToast(`Triggering AI Recovery workflow for Payment #${caseDetail.payment_id}...`, 'info');
      const res = await triggerPaymentFailed(caseDetail.payment_id);
      
      const recRes = res.recovery_result || {};
      const statusStr = recRes.final_status;
      const recoveredAmt = recRes.amount_recovered_paise || 0;

      if (statusStr === 'success') {
        if (onShowToast) onShowToast(`Recovery Succeeded! ${formatINR(recoveredAmt)} recovered.`, 'success');
      } else if (statusStr === 'stopped') {
        if (onShowToast) onShowToast(`Recovery Workflow Stopped: Customer opted out or policy blocked.`, 'warning');
      } else if (statusStr === 'escalated') {
        if (onShowToast) onShowToast(`Case Escalated to manual recovery queue.`, 'warning');
      } else {
        if (onShowToast) onShowToast(`Recovery workflow step executed.`, 'info');
      }

      const refreshed = await fetchRecoveryCase(caseId);
      setCaseDetail(refreshed);
      if (onRefreshData) onRefreshData();
    } catch (err: any) {
      if (onShowToast) onShowToast(`Trigger error: ${err.message}`, 'warning');
    } finally {
      setActionLoading(false);
    }
  };

  // Convert AuditLogs to TimelineEvents
  const mapAuditLogsToTimeline = (logs: AuditLog[] = []): TimelineEvent[] => {
    return logs.map((log) => {
      let actorType: TimelineEvent['type'] = 'system';
      if (log.actor === 'agent') actorType = 'agent';
      else if (log.actor === 'guardrail') actorType = 'guardrail';
      else if (log.actor === 'tool') actorType = 'tool';

      const titleFormatted = log.event_type
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, (l) => l.toUpperCase());

      return {
        id: `log-${log.id}`,
        title: titleFormatted,
        description: log.details || 'Event logged by backend system',
        type: actorType,
        timestamp: log.timestamp,
        status: log.event_type.includes('RECOVERED') || log.event_type.includes('succeeded')
          ? 'success'
          : log.event_type.includes('ESCALATED') || log.event_type.includes('blocked')
          ? 'warning'
          : 'info',
      };
    });
  };

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-sm)',
                background: '#eff6ff',
                color: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ShieldAlert size={20} />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>
                  Recovery Case #{caseId}
                </h2>
                {caseDetail && <Badge status={caseDetail.status} />}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                {caseDetail ? `Created ${formatTimestamp(caseDetail.created_at)} • Risk Score: ${caseDetail.risk_score || 45}/100` : 'Loading backend case data...'}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="btn btn-outline btn-sm"
            style={{ padding: '6px', borderRadius: '50%' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="drawer-body">
          {loading ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: '#64748b' }}>
              <RefreshCw size={24} className="spin-icon" style={{ marginBottom: '8px' }} />
              <div>Fetching case detail from backend...</div>
            </div>
          ) : error ? (
            <div style={{ padding: '24px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#991b1b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, marginBottom: '4px' }}>
                <AlertTriangle size={18} /> Error Loading Case
              </div>
              <div style={{ fontSize: '13px' }}>{error}</div>
            </div>
          ) : caseDetail ? (
            <>
              {/* Summary Box */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: '12px',
                  background: '#f8fafc',
                  border: '1px solid var(--neutral-border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 16px',
                  marginBottom: '20px',
                }}
              >
                <div>
                  <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>AMOUNT AT RISK</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', marginTop: '2px' }}>
                    {formatINR(caseDetail.amount_at_risk_paise)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>RECOVERED</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: caseDetail.amount_recovered_paise > 0 ? '#10b981' : '#64748b', marginTop: '2px' }}>
                    {formatINR(caseDetail.amount_recovered_paise)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>PAYMENT ID</div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#2563eb', marginTop: '4px' }}>
                    Payment #{caseDetail.payment_id}
                  </div>
                </div>
              </div>

              {/* Customer Metadata Card */}
              <div
                style={{
                  padding: '12px 16px',
                  background: '#ffffff',
                  border: '1px solid var(--neutral-border)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <User size={18} style={{ color: '#64748b' }} />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                      {caseDetail.customer_name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>
                      {caseDetail.customer_email}
                    </div>
                  </div>
                </div>

                {caseDetail.status === 'STOPPED' ? (
                  <span className="badge badge-neutral">
                    <Ban size={12} /> Opted Out / Stopped
                  </span>
                ) : (
                  <span className="badge badge-primary">Customer Active</span>
                )}
              </div>

              {/* Current State & Actions */}
              <div
                style={{
                  background: '#eff6ff',
                  border: '1px solid #bfdbfe',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 16px',
                  marginBottom: '24px',
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#1d4ed8', textTransform: 'uppercase' }}>
                  CURRENT WORKFLOW STEP
                </div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#1e3a8a', marginTop: '4px' }}>
                  {caseDetail.current_step || 'Workflow Active'}
                </div>
                <div style={{ fontSize: '12px', color: '#1e40af', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ArrowRight size={13} /> Attempt Count: {caseDetail.attempt_count}
                </div>
              </div>

              {/* Structured AI Decision Presentation */}
              {caseDetail.decision_reasoning && (
                <section style={{ marginBottom: '24px' }}>
                  <AIDecisionCard
                    decision={{
                      proposed_action: (caseDetail.decision_reasoning.proposed_action || 'retry_payment') as ActionType,
                      why: caseDetail.decision_reasoning.reason || 'Agent reasoning step complete',
                      policy_decision: caseDetail.decision_reasoning.policy_result === 'Blocked' ? 'Blocked' : 'Approved',
                      policy_reason: caseDetail.decision_reasoning.guardrail_note,
                      execution_result: caseDetail.status,
                      recovered_amount_paise: caseDetail.amount_recovered_paise,
                    }}
                  />
                </section>
              )}

              {/* Recovery Actions History Table */}
              <section style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  Recovery Actions Executed ({caseDetail.actions?.length || 0})
                </h3>
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Action Type</th>
                        <th>Policy</th>
                        <th>Result</th>
                        <th style={{ textAlign: 'right' }}>Recovered</th>
                      </tr>
                    </thead>
                    <tbody>
                      {caseDetail.actions && caseDetail.actions.length > 0 ? (
                        caseDetail.actions.map((act) => (
                          <tr key={act.id}>
                            <td style={{ fontWeight: 600, fontFamily: 'monospace', color: '#1e40af' }}>
                              {act.action_type}
                            </td>
                            <td>
                              <span className={`badge ${act.approved ? 'badge-success' : 'badge-danger'}`}>
                                {act.approved ? 'Approved' : 'Blocked'}
                              </span>
                            </td>
                            <td style={{ fontSize: '12px' }}>{act.result || 'Executed'}</td>
                            <td style={{ textAlign: 'right', fontWeight: 600, color: act.amount_recovered_paise > 0 ? '#10b981' : '#64748b' }}>
                              {formatINR(act.amount_recovered_paise)}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} style={{ textAlign: 'center', color: '#94a3b8', fontSize: '12px' }}>
                            No recovery actions recorded for this case yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Audit Timeline */}
              <section style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  Audit & Execution Timeline
                </h3>
                <TimelineStepper events={mapAuditLogsToTimeline(caseDetail.audit_logs)} />
              </section>

              {/* Quick Simulation Actions */}
              <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--neutral-border)', display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={actionLoading}
                  onClick={handleTriggerRecovery}
                >
                  <RefreshCw size={13} className={actionLoading ? 'spin-icon' : ''} /> Trigger AI Recovery Step
                </button>
                {caseDetail.status === 'IN_PROGRESS' && (
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={actionLoading}
                    onClick={handleSimulatePaymentCompletion}
                  >
                    <CheckCircle size={13} /> Simulate Customer Link Payment
                  </button>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};
