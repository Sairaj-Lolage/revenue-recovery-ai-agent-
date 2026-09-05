import React from 'react';
import { X, User, Mail, Phone, Ban, CheckCircle } from 'lucide-react';
import type { Customer, Payment, RecoveryCase } from '../../types';
import { Badge } from '../common/Badge';

interface CustomerDetailDrawerProps {
  customer: Customer | null;
  payments: Payment[];
  cases: RecoveryCase[];
  onClose: () => void;
  onSelectCase: (caseId: number) => void;
}

export const CustomerDetailDrawer: React.FC<CustomerDetailDrawerProps> = ({
  customer,
  payments,
  cases,
  onClose,
  onSelectCase,
}) => {
  if (!customer) return null;

  const customerPayments = payments.filter((p) => p.customer_id === customer.id);
  const customerCases = cases.filter((c) => c.customer_id === customer.id);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#e0e7ff',
                color: '#4338ca',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <User size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>{customer.name}</h2>
                {customer.opted_out ? (
                  <span className="badge badge-neutral">
                    <Ban size={12} /> Opted Out
                  </span>
                ) : (
                  <span className="badge badge-success">
                    <CheckCircle size={12} /> Active
                  </span>
                )}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>
                Segment: <strong>{customer.segment}</strong> • Member since {new Date(customer.created_at).toLocaleDateString()}
              </div>
            </div>
          </div>

          <button onClick={onClose} className="btn btn-outline btn-sm" style={{ padding: '6px', borderRadius: '50%' }}>
            <X size={18} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Customer KPI Summary */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: '12px',
              background: '#f8fafc',
              border: '1px solid var(--neutral-border)',
              borderRadius: 'var(--radius-md)',
              padding: '14px 16px',
              marginBottom: '20px',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>TOTAL PAID</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', marginTop: '2px' }}>
                ₹{(customer.total_paid_paise / 100).toLocaleString()}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>SUCCESSFUL PAYMENTS</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                {customer.successful_payments}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>FAILED PAYMENTS</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: customer.failed_payments > 0 ? '#ef4444' : '#64748b', marginTop: '2px' }}>
                {customer.failed_payments}
              </div>
            </div>
          </div>

          {/* Contact Details */}
          <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontSize: '13px', color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Mail size={15} style={{ color: '#94a3b8' }} /> {customer.email}
            </div>
            {customer.phone && (
              <div style={{ fontSize: '13px', color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Phone size={15} style={{ color: '#94a3b8' }} /> {customer.phone}
              </div>
            )}
          </div>

          {/* Opt-out Warning Banner */}
          {customer.opted_out && (
            <div
              style={{
                padding: '12px 16px',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: 'var(--radius-md)',
                marginBottom: '24px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
              }}
            >
              <Ban size={18} style={{ color: '#64748b', marginTop: '2px' }} />
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                  Automated Recovery Disabled (Opt-Out Policy)
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                  This customer has opted out of automated recovery messages and retries. The AI Agent will automatically halt any active cases for this account.
                </div>
              </div>
            </div>
          )}

          {/* Recovery Cases */}
          <section style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
              Associated Recovery Cases ({customerCases.length})
            </h3>
            {customerCases.length === 0 ? (
              <div style={{ fontSize: '13px', color: '#64748b', padding: '12px', background: '#f8fafc', borderRadius: 'var(--radius-sm)' }}>
                No recovery cases recorded for this customer.
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>Payment</th>
                      <th>At Risk</th>
                      <th>Status</th>
                      <th style={{ textAlign: 'right' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customerCases.map((c) => (
                      <tr key={c.id}>
                        <td style={{ fontWeight: 600 }}>Case #{c.id}</td>
                        <td>Payment #{c.payment_id}</td>
                        <td style={{ fontWeight: 600 }}>₹{(c.amount_at_risk_paise / 100).toLocaleString()}</td>
                        <td><Badge status={c.status} /></td>
                        <td style={{ textAlign: 'right' }}>
                          <button className="btn btn-outline btn-sm" onClick={() => onSelectCase(c.id)}>
                            View Case
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Payment History */}
          <section>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
              Payment History ({customerPayments.length})
            </h3>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Payment ID</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {customerPayments.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600 }}>Payment #{p.id}</td>
                      <td style={{ fontWeight: 600 }}>₹{(p.amount_paise / 100).toLocaleString()}</td>
                      <td><Badge status={p.status} /></td>
                      <td style={{ fontSize: '12px', color: '#64748b' }}>
                        {new Date(p.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
