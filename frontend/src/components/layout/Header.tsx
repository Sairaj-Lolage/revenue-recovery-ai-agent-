import React from 'react';
import { RefreshCw, Play } from 'lucide-react';
import { GlobalSearch } from '../common/GlobalSearch';
import type { Payment, RecoveryCase, Customer } from '../../types';

interface HeaderProps {
  payments: Payment[];
  cases: RecoveryCase[];
  customers: Customer[];
  onSelectPayment: (id: number) => void;
  onSelectCase: (id: number) => void;
  onSelectCustomer: (id: number) => void;
  onRefresh: () => void;
  onSimulateAction: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  payments,
  cases,
  customers,
  onSelectPayment,
  onSelectCase,
  onSelectCustomer,
  onRefresh,
  onSimulateAction,
  isRefreshing = false,
}) => {
  return (
    <header
      style={{
        height: '64px',
        background: '#ffffff',
        borderBottom: '1px solid var(--neutral-border)',
        padding: '0 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 80,
      }}
    >
      {/* Left: Global Search */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <GlobalSearch
          payments={payments}
          cases={cases}
          customers={customers}
          onSelectPayment={onSelectPayment}
          onSelectCase={onSelectCase}
          onSelectCustomer={onSelectCustomer}
        />
      </div>

      {/* Right: Environment, Quick Actions & Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Environment Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: '#f1f5f9',
            border: '1px solid var(--neutral-border)',
            borderRadius: 'var(--radius-full)',
            padding: '4px 12px',
            fontSize: '12px',
            fontWeight: 500,
            color: '#334155',
          }}
          title="Payment simulation engine active for testing"
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#3b82f6',
              boxShadow: '0 0 0 2px #dbeafe',
            }}
          />
          <span>Simulation Mode</span>
        </div>

        {/* Refresh Button */}
        <button
          className="btn btn-outline btn-sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh dashboard state"
        >
          <RefreshCw
            size={14}
            className={isRefreshing ? 'spin' : ''}
            style={{
              animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
            }}
          />
          <span>{isRefreshing ? 'Updating...' : 'Refresh'}</span>
        </button>

        {/* Demo Simulation Action Button */}
        <button
          className="btn btn-primary btn-sm"
          onClick={onSimulateAction}
          title="Trigger a simulated payment event or recovery step"
        >
          <Play size={13} fill="currentColor" />
          <span>Simulate Event</span>
        </button>

        {/* Divider */}
        <div style={{ width: '1px', height: '24px', background: 'var(--neutral-border)' }} />

        {/* User Profile */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: '#e2e8f0',
              color: '#334155',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 600,
              fontSize: '13px',
            }}
          >
            OM
          </div>
          <div style={{ fontSize: '13px' }}>
            <div style={{ fontWeight: 600, color: '#0f172a', lineHeight: 1.1 }}>Ops Team</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Fintech Admin</div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </header>
  );
};
