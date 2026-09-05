import React from 'react';
import { Bot, Shield, Zap, CheckCircle2 } from 'lucide-react';

interface AgentStatusWidgetProps {
  recoveriesToday: number;
}

export const AgentStatusWidget: React.FC<AgentStatusWidgetProps> = ({ recoveriesToday }) => {
  return (
    <div className="card" style={{ background: '#f8fafc', borderColor: '#cbd5e1' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: 'var(--radius-sm)',
              background: '#2563eb',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Bot size={16} />
          </div>
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>AI Recovery Agent</h4>
            <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#10b981',
                  display: 'inline-block',
                }}
              />
              Active & Monitoring
            </div>
          </div>
        </div>

        <span className="badge badge-success">
          <Zap size={11} /> Autonomous
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
          padding: '10px',
          background: '#ffffff',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--neutral-border)',
          marginBottom: '12px',
        }}
      >
        <div>
          <div style={{ fontSize: '11px', color: '#64748b' }}>Recovered Today</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#10b981' }}>{recoveriesToday} cases</div>
        </div>
        <div>
          <div style={{ fontSize: '11px', color: '#64748b' }}>Guardrails Active</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#2563eb', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Shield size={14} /> 5 Rules
          </div>
        </div>
      </div>

      <div style={{ fontSize: '11px', color: '#64748b', lineHeight: 1.4 }}>
        <CheckCircle2 size={12} style={{ color: '#10b981', verticalAlign: 'middle', marginRight: '4px' }} />
        All recovery actions run through policy enforcement guardrails before execution.
      </div>
    </div>
  );
};
