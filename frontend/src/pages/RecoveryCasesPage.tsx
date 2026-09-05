import React, { useState } from 'react';
import { Search, ArrowUpRight } from 'lucide-react';
import type { RecoveryCase } from '../types';
import { formatINR } from '../utils/formatters';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

interface RecoveryCasesPageProps {
  cases: RecoveryCase[];
  onSelectCase: (caseId: number) => void;
}

export const RecoveryCasesPage: React.FC<RecoveryCasesPageProps> = ({ cases, onSelectCase }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      searchTerm === '' ||
      c.id.toString().includes(searchTerm) ||
      c.payment_id.toString().includes(searchTerm) ||
      c.customer_name?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Recovery Operations Center</h1>
          <p className="page-subtitle">
            Manage active AI recovery cases, customer workflow lifecycles, and policy guardrail interventions.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="card"
        style={{
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: '#f8fafc',
            border: '1px solid var(--neutral-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 12px',
            width: '280px',
          }}
        >
          <Search size={15} style={{ color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search Case #, Payment # or Customer..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: '13px', width: '100%' }}
          />
        </div>

        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {(['ALL', 'OPEN', 'IN_PROGRESS', 'RECOVERED', 'ESCALATED', 'STOPPED'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                border: '1px solid',
                borderColor: statusFilter === st ? '#2563eb' : 'var(--neutral-border)',
                background: statusFilter === st ? '#eff6ff' : '#ffffff',
                color: statusFilter === st ? '#1d4ed8' : '#64748b',
                fontWeight: statusFilter === st ? 600 : 500,
                fontSize: '12px',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
              }}
            >
              {st === 'ALL' ? 'All Statuses' : st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Cases Table */}
      {filteredCases.length === 0 ? (
        <EmptyState
          title="No recovery cases found"
          description="There are no recovery cases matching the selected search or status filters."
          actionText="Show All Cases"
          onAction={() => {
            setSearchTerm('');
            setStatusFilter('ALL');
          }}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Payment</th>
                <th>Customer</th>
                <th style={{ textAlign: 'right' }}>Amount at Risk</th>
                <th>Recovery Status</th>
                <th style={{ textAlign: 'right' }}>Amount Recovered</th>
                <th>Risk Score</th>
                <th>Current State</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.map((c) => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 700, color: '#0f172a' }}>
                    Case #{c.id}
                  </td>
                  <td style={{ fontWeight: 600, color: '#2563eb' }}>
                    Payment #{c.payment_id}
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>{c.customer_name}</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>{c.customer_email}</div>
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>
                    {formatINR(c.amount_at_risk_paise)}
                  </td>
                  <td>
                    <Badge status={c.status} />
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 700, color: c.amount_recovered_paise > 0 ? '#10b981' : '#64748b' }}>
                    {formatINR(c.amount_recovered_paise)}
                  </td>
                  <td>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: (c.risk_score || 0) > 70 ? '#fee2e2' : (c.risk_score || 0) > 40 ? '#fef3c7' : '#dcfce7',
                        color: (c.risk_score || 0) > 70 ? '#991b1b' : (c.risk_score || 0) > 40 ? '#92400e' : '#166534',
                      }}
                    >
                      {c.risk_score || 45}/100
                    </span>
                  </td>
                  <td style={{ fontSize: '12px', color: '#475569', maxWidth: '180px' }}>
                    {c.current_step || 'Active'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onSelectCase(c.id)}
                    >
                      <span>Investigate</span>
                      <ArrowUpRight size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
