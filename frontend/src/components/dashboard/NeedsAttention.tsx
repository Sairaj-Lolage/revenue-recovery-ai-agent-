import React from 'react';
import { AlertTriangle, ArrowRight, ShieldAlert, Clock, Ban } from 'lucide-react';
import type { RecoveryCase } from '../../types';
import { Badge } from '../common/Badge';

interface NeedsAttentionProps {
  cases: RecoveryCase[];
  onSelectCase: (caseId: number) => void;
}

export const NeedsAttention: React.FC<NeedsAttentionProps> = ({ cases, onSelectCase }) => {
  // Filter cases that need operator awareness (IN_PROGRESS, ESCALATED, STOPPED)
  const attentionCases = cases.filter(
    (c) => c.status === 'IN_PROGRESS' || c.status === 'ESCALATED' || c.status === 'STOPPED'
  );

  return (
    <div className="card" style={{ borderLeft: '4px solid #f59e0b' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} style={{ color: '#d97706' }} />
          <h3 className="card-title">Needs Attention</h3>
        </div>
        <span className="badge badge-warning">{attentionCases.length} Items Require Review</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
        {attentionCases.map((c) => {
          const isEscalated = c.status === 'ESCALATED';
          const isStopped = c.status === 'STOPPED';

          return (
            <div
              key={c.id}
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                background: isEscalated ? '#fef2f2' : isStopped ? '#f8fafc' : '#fffbeb',
                border: `1px solid ${isEscalated ? '#fecaca' : isStopped ? '#e2e8f0' : '#fde68a'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: isEscalated ? '#ef4444' : isStopped ? '#64748b' : '#f59e0b',
                    boxShadow: 'var(--shadow-sm)',
                  }}
                >
                  {isEscalated ? <ShieldAlert size={16} /> : isStopped ? <Ban size={16} /> : <Clock size={16} />}
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '13px', color: '#0f172a' }}>
                      Payment #{c.payment_id}
                    </span>
                    <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                      ₹{(c.amount_at_risk_paise / 100).toLocaleString()}
                    </span>
                    <Badge status={c.status} />
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                    {c.customer_name} • {c.current_step || c.failure_reason}
                  </div>
                </div>
              </div>

              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onSelectCase(c.id)}
                style={{ background: '#ffffff' }}
              >
                <span>{isEscalated ? 'Review Case' : 'View Details'}</span>
                <ArrowRight size={13} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
