import React, { useEffect, useState } from 'react';
import { Shield, CheckCircle2, Play, RefreshCw } from 'lucide-react';
import { fetchPolicySettings, triggerPaymentFailed, updatePolicySettings } from '../api';
import { formatINR } from '../utils/formatters';

interface SettingsPageProps {
  onTriggerToast: (text: string, type?: 'success' | 'info' | 'warning') => void;
  onRefreshData?: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ onTriggerToast, onRefreshData }) => {
  const [maxRetries, setMaxRetries] = useState(2);
  const [highValueThreshold, setHighValueThreshold] = useState(10000);
  const [simPaymentId, setSimPaymentId] = useState<number>(67);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPolicySettings()
      .then((settings) => {
        setMaxRetries(settings.max_retry_attempts);
        setHighValueThreshold(settings.high_value_threshold_paise / 100);
      })
      .catch(() => onTriggerToast('Unable to load policy settings from the backend.', 'warning'));
  }, [onTriggerToast]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updatePolicySettings({
        max_retry_attempts: maxRetries,
        high_value_threshold_paise: Math.round(highValueThreshold * 100),
      });
      onTriggerToast('Guardrail policy settings saved and will apply to new recovery runs.', 'success');
    } catch (err: any) {
      onTriggerToast(`Unable to save policy settings: ${err.message}`, 'warning');
    } finally {
      setSaving(false);
    }
  };

  const handleSimulatePaymentFailure = async () => {
    setLoading(true);
    try {
      onTriggerToast(`Dispatching payment.failed event for Payment #${simPaymentId}...`, 'info');
      const res = await triggerPaymentFailed(simPaymentId);
      
      const recRes = res.recovery_result || {};
      const statusStr = recRes.final_status;
      const recoveredAmt = recRes.amount_recovered_paise || 0;

      if (statusStr === 'success') {
        onTriggerToast(`Payment #${simPaymentId} recovered! ${formatINR(recoveredAmt)} recovered via automatic retry.`, 'success');
      } else if (statusStr === 'stopped') {
        onTriggerToast(`Recovery stopped for Payment #${simPaymentId}: Customer opted out or policy blocked.`, 'warning');
      } else if (statusStr === 'escalated') {
        onTriggerToast(`Recovery escalated for Payment #${simPaymentId}: Case sent to manual queue.`, 'warning');
      } else {
        onTriggerToast(`Payment failure ingested. AI Recovery in progress for Payment #${simPaymentId}.`, 'info');
      }

      if (onRefreshData) onRefreshData();
    } catch (err: any) {
      onTriggerToast(`Simulation error: ${err.message}`, 'warning');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '900px' }}>
      {/* Page Header */}
      <div>
        <h1 className="page-title">Settings & Policy Guardrails</h1>
        <p className="page-subtitle">
          Configure safety guardrail rules, autonomous agent thresholds, and recovery simulation parameters.
        </p>
      </div>

      {/* Safety Policy Guardrails Card */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: '#eff6ff',
                color: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Shield size={18} />
            </div>
            <div>
              <h3 className="card-title">AI Safety Guardrails</h3>
              <p style={{ fontSize: '12px', color: '#64748b' }}>Deterministic limits enforced prior to every action execution</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '12px' }}>
          {/* Rule 1: Max Retry Attempts */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '16px', borderBottom: '1px solid #f1f5f9' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>Maximum Payment Retry Limit</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Maximum automated card retry attempts per failed payment</div>
            </div>
            <select
              value={maxRetries}
              onChange={(e) => setMaxRetries(Number(e.target.value))}
              style={{ padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid #cbd5e1', fontSize: '13px' }}
            >
              <option value={1}>1 Retry</option>
              <option value={2}>2 Retries</option>
              <option value={3}>3 Retries</option>
            </select>
          </div>

          {/* Rule 2: High Value Threshold */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '16px', borderBottom: '1px solid #f1f5f9' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>High-Value Escalation Threshold</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Transactions equal or above this amount automatically escalate to human operators</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b' }}>₹</span>
              <input
                type="number"
                value={highValueThreshold}
                onChange={(e) => setHighValueThreshold(Number(e.target.value))}
                style={{ padding: '6px 12px', width: '110px', borderRadius: 'var(--radius-sm)', border: '1px solid #cbd5e1', fontSize: '13px', fontWeight: 600 }}
              />
            </div>
          </div>

          {/* Rule 3: Customer Opt-Out Respect */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '16px', borderBottom: '1px solid #f1f5f9' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>Strict Opt-Out Compliance Enforcer</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Hard stop: Zero messages or retries for customers flagged as opted-out</div>
            </div>
            <input type="checkbox" checked disabled aria-label="Opt-out enforcement is always enabled" style={{ width: '18px', height: '18px' }} />
          </div>

          {/* Rule 4: Expiration Delay */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>Payment Link Expiration Escalation Window</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Auto-escalate case if recovery link remains unpaid after specified hours</div>
            </div>
            <span style={{ fontSize: '13px', color: '#64748b', fontWeight: 600 }}>Not scheduled in MVP</span>
          </div>
        </div>

        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <CheckCircle2 size={16} /> {saving ? 'Saving…' : 'Save Guardrail Configurations'}
          </button>
        </div>
      </div>

      {/* Simulation Engine Controls Card */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: '#fef3c7',
                color: '#d97706',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Play size={18} />
            </div>
            <div>
              <h3 className="card-title">Backend Recovery Trigger Simulator</h3>
              <p style={{ fontSize: '12px', color: '#64748b' }}>Dispatch payment.failed events directly to POST /api/events/payment-failed</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Target Payment ID:</label>
            <input
              type="number"
              value={simPaymentId}
              onChange={(e) => setSimPaymentId(Number(e.target.value))}
              style={{ padding: '6px 12px', width: '90px', borderRadius: 'var(--radius-sm)', border: '1px solid #cbd5e1', fontSize: '13px', fontWeight: 600 }}
            />
          </div>

          <button
            className="btn btn-primary"
            disabled={loading}
            onClick={handleSimulatePaymentFailure}
          >
            {loading ? <RefreshCw size={14} className="spin-icon" /> : <Play size={14} />}
            <span>Trigger Payment Failure Event</span>
          </button>
        </div>
      </div>
    </div>
  );
};
