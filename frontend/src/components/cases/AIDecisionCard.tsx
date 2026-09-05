import React from 'react';
import { Bot, ShieldCheck, ShieldAlert, CheckCircle, AlertCircle } from 'lucide-react';
import type { AIDecision } from '../../types';

interface AIDecisionCardProps {
  decision: AIDecision;
}

export const AIDecisionCard: React.FC<AIDecisionCardProps> = ({ decision }) => {
  const isApproved = decision.policy_decision === 'Approved';

  return (
    <div
      style={{
        background: '#ffffff',
        border: `1px solid ${isApproved ? 'var(--primary-100)' : 'var(--danger-border)'}`,
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '20px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: 'var(--radius-sm)',
              background: isApproved ? 'var(--primary-500)' : '#dc2626',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Bot size={16} />
          </div>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a' }}>AI Decision Summary</h4>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Structured Operational Reasoning</div>
          </div>
        </div>

        <div
          className={`badge ${isApproved ? 'badge-success' : 'badge-danger'}`}
          style={{ fontSize: '12px' }}
        >
          {isApproved ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
          <span>Policy {decision.policy_decision}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Proposed Action */}
        <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>PROPOSED ACTION</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#1e40af', marginTop: '2px', fontFamily: 'monospace' }}>
            {decision.proposed_action}
          </div>
        </div>

        {/* Execution Result */}
        <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>EXECUTION RESULT</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: isApproved ? '#065f46' : '#991b1b', marginTop: '2px' }}>
            {decision.execution_result}
          </div>
        </div>
      </div>

      {/* Reasoning */}
      <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px border #f1f5f9' }}>
        <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', marginBottom: '4px' }}>
          Why AI Selected This Action
        </div>
        <p style={{ fontSize: '13px', color: '#334155', lineHeight: 1.4 }}>
          {decision.why}
        </p>
      </div>

      {/* Policy Guardrail details */}
      {decision.policy_reason && (
        <div style={{ marginTop: '10px', fontSize: '12px', color: isApproved ? '#1e40af' : '#991b1b', display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isApproved ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
          <span><strong>Guardrail Note:</strong> {decision.policy_reason}</span>
        </div>
      )}
    </div>
  );
};
