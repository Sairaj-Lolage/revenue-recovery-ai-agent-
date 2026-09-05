import React, { useState } from 'react';
import { Search, ArrowUpRight, Zap } from 'lucide-react';
import type { Payment } from '../types';
import { formatINR, formatTimestamp } from '../utils/formatters';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

interface PaymentsPageProps {
  payments: Payment[];
  onSelectPayment?: (id: number) => void;
  onSelectCase: (caseId: number) => void;
  onSimulateRecovery?: (paymentId: number) => void;
}

export const PaymentsPage: React.FC<PaymentsPageProps> = ({
  payments,
  onSelectCase,
  onSimulateRecovery,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [recoveryFilter, setRecoveryFilter] = useState<string>('ALL');

  const filteredPayments = payments.filter((p) => {
    const matchesSearch =
      searchTerm === '' ||
      p.id.toString().includes(searchTerm) ||
      p.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.customer_email?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'ALL' || p.status.toUpperCase() === statusFilter;
    const matchesRecovery =
      recoveryFilter === 'ALL' || (p.case_status && p.case_status === recoveryFilter);

    return matchesSearch && matchesStatus && matchesRecovery;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Payments</h1>
          <p className="page-subtitle">
            Inspect transaction history, payment failures, and associated AI recovery lifecycles.
          </p>
        </div>
      </div>

      {/* Filter Controls Bar */}
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
        {/* Search */}
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
            placeholder="Search by Payment # or Customer..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: '13px', width: '100%' }}
          />
        </div>

        {/* Dropdown Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>Payment Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                padding: '6px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--neutral-border)',
                background: '#ffffff',
                fontSize: '13px',
                color: '#0f172a',
              }}
            >
              <option value="ALL">All Statuses</option>
              <option value="FAILED">Failed</option>
              <option value="SUCCESS">Success</option>
              <option value="PENDING">Pending</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>Recovery Status:</span>
            <select
              value={recoveryFilter}
              onChange={(e) => setRecoveryFilter(e.target.value)}
              style={{
                padding: '6px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--neutral-border)',
                background: '#ffffff',
                fontSize: '13px',
                color: '#0f172a',
              }}
            >
              <option value="ALL">All Cases</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RECOVERED">Recovered</option>
              <option value="ESCALATED">Escalated</option>
              <option value="STOPPED">Stopped</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Section */}
      {filteredPayments.length === 0 ? (
        <EmptyState
          title="No payments match filters"
          description="Try adjusting search parameters or clearing active filters."
          actionText="Clear Filters"
          onAction={() => {
            setSearchTerm('');
            setStatusFilter('ALL');
            setRecoveryFilter('ALL');
          }}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Payment ID</th>
                <th>Customer</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Payment Status</th>
                <th>Recovery Status</th>
                <th>Last Recovery Action</th>
                <th>Created</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayments.map((payment) => {
                const caseId = payment.case_id || payment.recovery_case_id;
                const caseStatus = payment.case_status || payment.recovery_status;

                return (
                  <tr key={payment.id}>
                    <td style={{ fontWeight: 700, color: '#0f172a' }}>
                      #{payment.id}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>
                        {payment.customer_name || 'Customer'}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        {payment.customer_email || ''}
                      </div>
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>
                      {formatINR(payment.amount_paise)}
                    </td>
                    <td>
                      <Badge status={payment.status} />
                    </td>
                    <td>
                      {caseStatus ? (
                        <Badge status={caseStatus} />
                      ) : (
                        <span style={{ fontSize: '12px', color: '#94a3b8' }}>Unprocessed</span>
                      )}
                    </td>
                    <td style={{ fontSize: '12px', color: '#475569', maxWidth: '200px' }}>
                      {payment.last_action || 'None'}
                    </td>
                    <td style={{ fontSize: '12px', color: '#64748b' }}>
                      {formatTimestamp(payment.created_at)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        {caseId ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => onSelectCase(caseId)}
                          >
                            <span>View Case</span>
                            <ArrowUpRight size={13} />
                          </button>
                        ) : payment.status === 'success' ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled
                            title="Successful payments do not need recovery."
                          >
                            <Zap size={12} />
                            <span>Already Paid</span>
                          </button>
                        ) : (
                          onSimulateRecovery && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => onSimulateRecovery(payment.id)}
                            >
                              <Zap size={12} />
                              <span>Run Agent</span>
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
