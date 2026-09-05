import React, { useState } from 'react';
import { Search, Ban, CheckCircle2, ArrowUpRight } from 'lucide-react';
import type { Customer } from '../types';
import { formatINR } from '../utils/formatters';

interface CustomersPageProps {
  customers: Customer[];
  onSelectCustomer: (customerId: number) => void;
}

export const CustomersPage: React.FC<CustomersPageProps> = ({ customers, onSelectCustomer }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [optOutFilter, setOptOutFilter] = useState<'ALL' | 'ACTIVE' | 'OPTED_OUT'>('ALL');

  const filteredCustomers = customers.filter((cust) => {
    const matchesSearch =
      searchTerm === '' ||
      cust.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cust.email.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesOptOut =
      optOutFilter === 'ALL' ||
      (optOutFilter === 'OPTED_OUT' && cust.opted_out) ||
      (optOutFilter === 'ACTIVE' && !cust.opted_out);

    return matchesSearch && matchesOptOut;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Customers</h1>
          <p className="page-subtitle">
            Customer directory, subscription segments, total paid revenue, and recovery opt-out statuses.
          </p>
        </div>
      </div>

      {/* Filter Controls */}
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
            placeholder="Search by Customer name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: '13px', width: '100%' }}
          />
        </div>

        {/* Opt out filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {(['ALL', 'ACTIVE', 'OPTED_OUT'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setOptOutFilter(filter)}
              style={{
                border: '1px solid',
                borderColor: optOutFilter === filter ? '#2563eb' : 'var(--neutral-border)',
                background: optOutFilter === filter ? '#eff6ff' : '#ffffff',
                color: optOutFilter === filter ? '#1d4ed8' : '#64748b',
                fontWeight: optOutFilter === filter ? 600 : 500,
                fontSize: '12px',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
              }}
            >
              {filter === 'ALL' ? 'All Customers' : filter === 'ACTIVE' ? 'Active' : 'Opted Out'}
            </button>
          ))}
        </div>
      </div>

      {/* Customers Table */}
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Segment</th>
              <th style={{ textAlign: 'right' }}>Total Paid</th>
              <th style={{ textAlign: 'center' }}>Successful</th>
              <th style={{ textAlign: 'center' }}>Failed</th>
              <th>Opt-out Status</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredCustomers.map((cust) => (
              <tr key={cust.id}>
                <td>
                  <div style={{ fontWeight: 600, color: '#0f172a' }}>{cust.name}</div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>{cust.email}</div>
                </td>
                <td>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: '#f1f5f9',
                      color: '#334155',
                    }}
                  >
                    {cust.segment}
                  </span>
                </td>
                <td style={{ textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>
                  {formatINR(cust.total_paid_paise)}
                </td>
                <td style={{ textAlign: 'center', fontWeight: 600, color: '#10b981' }}>
                  {cust.successful_payments}
                </td>
                <td style={{ textAlign: 'center', fontWeight: 600, color: cust.failed_payments > 0 ? '#ef4444' : '#64748b' }}>
                  {cust.failed_payments}
                </td>
                <td>
                  {cust.opted_out ? (
                    <span className="badge badge-neutral">
                      <Ban size={12} /> Opted Out
                    </span>
                  ) : (
                    <span className="badge badge-success">
                      <CheckCircle2 size={12} /> Active Recovery
                    </span>
                  )}
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => onSelectCustomer(cust.id)}
                  >
                    <span>View Customer</span>
                    <ArrowUpRight size={13} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
