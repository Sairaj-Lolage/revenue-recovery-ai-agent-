import React from 'react';
import { AlertOctagon, Bot, RefreshCw, Link2, CheckCircle } from 'lucide-react';

export const RecoveryFunnel: React.FC = () => {
  const funnelSteps = [
    {
      id: 'failed',
      label: 'Failed Payments',
      count: 15,
      amount: '₹36,795',
      icon: AlertOctagon,
      color: '#ef4444',
      bgColor: '#fef2f2',
    },
    {
      id: 'diagnosed',
      label: 'AI Started',
      count: 15,
      amount: '100% evaluated',
      icon: Bot,
      color: '#3b82f6',
      bgColor: '#eff6ff',
    },
    {
      id: 'retry',
      label: 'Auto Retry',
      count: 8,
      amount: '3 recovered',
      icon: RefreshCw,
      color: '#6366f1',
      bgColor: '#e0e7ff',
    },
    {
      id: 'link',
      label: 'Payment Link',
      count: 5,
      amount: 'SMS / WhatsApp',
      icon: Link2,
      color: '#d97706',
      bgColor: '#fffbeb',
    },
    {
      id: 'recovered',
      label: 'Recovered / Closed',
      count: 4,
      amount: '₹13,998 recovered',
      icon: CheckCircle,
      color: '#10b981',
      bgColor: '#ecfdf5',
    },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Recovery Lifecycle Progression</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Automated recovery pipeline conversion flow
          </p>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '12px',
          marginTop: '8px',
        }}
      >
        {funnelSteps.map((step, idx) => {
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              style={{
                background: step.bgColor,
                border: `1px solid ${step.color}30`,
                borderRadius: 'var(--radius-md)',
                padding: '12px 14px',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div
                  style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    background: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: step.color,
                  }}
                >
                  <Icon size={14} />
                </div>
                <span style={{ fontSize: '11px', fontWeight: 600, color: step.color }}>
                  Step {idx + 1}
                </span>
              </div>

              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                  {step.label}
                </div>
                <div style={{ fontSize: '16px', fontWeight: 700, color: step.color, marginTop: '2px' }}>
                  {step.count} <span style={{ fontSize: '11px', fontWeight: 400, color: '#64748b' }}>cases</span>
                </div>
                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                  {step.amount}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
