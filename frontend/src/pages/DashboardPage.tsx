import React from 'react';
import { Calendar } from 'lucide-react';
import type { RecoveryCase, AuditLog, DashboardKPIS } from '../types';
import { KPICardGroup } from '../components/dashboard/KPICardGroup';
import { PerformanceChart } from '../components/dashboard/PerformanceChart';
import { RecoveryFunnel } from '../components/dashboard/RecoveryFunnel';
import { NeedsAttention } from '../components/dashboard/NeedsAttention';
import { RecentActivity } from '../components/dashboard/RecentActivity';
import { AgentStatusWidget } from '../components/dashboard/AgentStatusWidget';

interface DashboardPageProps {
  kpis: DashboardKPIS;
  cases: RecoveryCase[];
  auditLogs: AuditLog[];
  onSelectCase: (caseId: number) => void;
  onNavigateToTab: (tab: any) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  kpis,
  cases,
  auditLogs,
  onSelectCase,
  onNavigateToTab,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Title & Quick Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Recovery Overview</h1>
          <p className="page-subtitle">
            Monitor failed payments, AI recovery workflow performance, and operator escalations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#ffffff',
              border: '1px solid var(--neutral-border)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 12px',
              fontSize: '13px',
              color: '#334155',
            }}
          >
            <Calendar size={14} style={{ color: '#94a3b8' }} />
            <span>Last 30 Days</span>
          </div>
        </div>
      </div>

      {/* Unified Single Container Card for Metric Boxes */}
      <KPICardGroup kpis={kpis} onNavigateToTab={onNavigateToTab} />

      {/* Main Dashboard Layout Grid */}
      <div className="dashboard-grid">
        {/* Left Column: Analytics & Funnel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <PerformanceChart />
          <RecoveryFunnel />
          <RecentActivity auditLogs={auditLogs} onSelectCase={onSelectCase} />
        </div>

        {/* Right Column: Operator Actions & Agent Status */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <AgentStatusWidget recoveriesToday={kpis.totalRecoveriesToday} />
          <NeedsAttention cases={cases} onSelectCase={onSelectCase} />
        </div>
      </div>
    </div>
  );
};
