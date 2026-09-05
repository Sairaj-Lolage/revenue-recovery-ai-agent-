import React from 'react';
import { AlertCircle, CheckCircle2, Clock, ShieldAlert, Ban } from 'lucide-react';
import type { DashboardKPIS } from '../../types';

interface KPICardGroupProps {
  kpis: DashboardKPIS;
  onNavigateToTab: (tab: 'payments' | 'cases' | 'customers' | 'audit' | 'settings') => void;
}

export const KPICardGroup: React.FC<KPICardGroupProps> = ({ kpis, onNavigateToTab }) => {
  const metrics = [
    {
      id: 'at_risk',
      title: 'Amount at Risk',
      value: `₹${(kpis.amountAtRiskPaise / 100).toLocaleString()}`,
      subtext: `${kpis.failedCount} failed payments`,
      icon: AlertCircle,
      iconBg: '#fef2f2',
      iconColor: '#ef4444',
      onClick: () => onNavigateToTab('payments'),
    },
    {
      id: 'recovered',
      title: 'Recovered Revenue',
      value: `₹${(kpis.recoveredAmountPaise / 100).toLocaleString()}`,
      subtext: `${kpis.recoveryRatePercent}% recovery rate`,
      icon: CheckCircle2,
      iconBg: '#ecfdf5',
      iconColor: '#10b981',
      onClick: () => onNavigateToTab('cases'),
    },
    {
      id: 'in_progress',
      title: 'In Progress',
      value: kpis.inProgressCount.toString(),
      subtext: 'Awaiting customer payment',
      icon: Clock,
      iconBg: '#fffbeb',
      iconColor: '#f59e0b',
      onClick: () => onNavigateToTab('cases'),
    },
    {
      id: 'escalated',
      title: 'Escalated',
      value: kpis.escalatedCount.toString(),
      subtext: 'Requires human attention',
      icon: ShieldAlert,
      iconBg: '#fef2f2',
      iconColor: '#dc2626',
      onClick: () => onNavigateToTab('cases'),
    },
    {
      id: 'stopped',
      title: 'Stopped',
      value: kpis.stoppedCount.toString(),
      subtext: 'Policy / opt-out hard stop',
      icon: Ban,
      iconBg: '#f1f5f9',
      iconColor: '#64748b',
      onClick: () => onNavigateToTab('cases'),
    },
  ];

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        }}
      >
        {metrics.map((m, idx) => {
          const Icon = m.icon;
          const isLast = idx === metrics.length - 1;

          return (
            <div
              key={m.id}
              onClick={m.onClick}
              style={{
                padding: '18px 20px',
                borderRight: isLast ? 'none' : '1px solid var(--neutral-border)',
                borderBottom: '1px solid transparent',
                cursor: 'pointer',
                transition: 'background 0.15s ease-in-out',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#f8fafc';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>
                  {m.title}
                </span>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: 'var(--radius-sm)',
                    background: m.iconBg,
                    color: m.iconColor,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Icon size={18} />
                </div>
              </div>

              <div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.02em', marginBottom: '2px' }}>
                  {m.value}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {m.subtext}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
