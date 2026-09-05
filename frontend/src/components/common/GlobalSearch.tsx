import React, { useState, useEffect, useRef } from 'react';
import { Search, CreditCard, User, ShieldAlert, X, ArrowRight } from 'lucide-react';
import type { Payment, RecoveryCase, Customer } from '../../types';

interface GlobalSearchProps {
  payments: Payment[];
  cases: RecoveryCase[];
  customers: Customer[];
  onSelectPayment: (paymentId: number) => void;
  onSelectCase: (caseId: number) => void;
  onSelectCustomer: (customerId: number) => void;
}

export const GlobalSearch: React.FC<GlobalSearchProps> = ({
  payments,
  cases,
  customers,
  onSelectPayment,
  onSelectCase,
  onSelectCustomer,
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const cleanQ = query.trim().toLowerCase();

  const matchingPayments = cleanQ
    ? payments.filter(
        (p) =>
          p.id.toString().includes(cleanQ) ||
          p.customer_name?.toLowerCase().includes(cleanQ) ||
          p.customer_email?.toLowerCase().includes(cleanQ)
      )
    : [];

  const matchingCases = cleanQ
    ? cases.filter(
        (c) =>
          c.id.toString().includes(cleanQ) ||
          c.payment_id.toString().includes(cleanQ) ||
          c.customer_name?.toLowerCase().includes(cleanQ)
      )
    : [];

  const matchingCustomers = cleanQ
    ? customers.filter(
        (cust) =>
          cust.name.toLowerCase().includes(cleanQ) ||
          cust.email.toLowerCase().includes(cleanQ)
      )
    : [];

  const hasResults =
    matchingPayments.length > 0 || matchingCases.length > 0 || matchingCustomers.length > 0;

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '320px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: '#ffffff',
          border: '1px solid var(--neutral-border)',
          borderRadius: 'var(--radius-sm)',
          padding: '6px 12px',
          transition: 'all 0.15s ease',
        }}
      >
        <Search size={15} style={{ color: '#94a3b8' }} />
        <input
          type="text"
          placeholder="Search payment 67, customer Rahul, case 2..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          style={{
            border: 'none',
            outline: 'none',
            fontSize: '13px',
            width: '100%',
            color: '#0f172a',
            background: 'transparent',
          }}
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setIsOpen(false);
            }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
          >
            <X size={14} />
          </button>
        )}
      </div>

      {isOpen && cleanQ && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: 0,
            width: '420px',
            background: '#ffffff',
            border: '1px solid var(--neutral-border)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 200,
            maxHeight: '400px',
            overflowY: 'auto',
            padding: '8px 0',
          }}
        >
          {!hasResults ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
              No matches found for "{query}"
            </div>
          ) : (
            <>
              {matchingCases.length > 0 && (
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ padding: '4px 12px', fontSize: '11px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                    Recovery Cases
                  </div>
                  {matchingCases.map((c) => (
                    <div
                      key={`c-${c.id}`}
                      onClick={() => {
                        onSelectCase(c.id);
                        setIsOpen(false);
                        setQuery('');
                      }}
                      style={{
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#f8fafc')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <ShieldAlert size={15} style={{ color: '#3b82f6' }} />
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 500, color: '#0f172a' }}>
                            Case #{c.id} (Payment #{c.payment_id})
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            {c.customer_name} • ₹{(c.amount_at_risk_paise / 100).toLocaleString()} • {c.status}
                          </div>
                        </div>
                      </div>
                      <ArrowRight size={14} style={{ color: '#cbd5e1' }} />
                    </div>
                  ))}
                </div>
              )}

              {matchingPayments.length > 0 && (
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ padding: '4px 12px', fontSize: '11px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                    Payments
                  </div>
                  {matchingPayments.map((p) => (
                    <div
                      key={`p-${p.id}`}
                      onClick={() => {
                        onSelectPayment(p.id);
                        setIsOpen(false);
                        setQuery('');
                      }}
                      style={{
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#f8fafc')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <CreditCard size={15} style={{ color: '#10b981' }} />
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 500, color: '#0f172a' }}>
                            Payment #{p.id}
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            {p.customer_name} • ₹{(p.amount_paise / 100).toLocaleString()} • {p.status}
                          </div>
                        </div>
                      </div>
                      <ArrowRight size={14} style={{ color: '#cbd5e1' }} />
                    </div>
                  ))}
                </div>
              )}

              {matchingCustomers.length > 0 && (
                <div>
                  <div style={{ padding: '4px 12px', fontSize: '11px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                    Customers
                  </div>
                  {matchingCustomers.map((cust) => (
                    <div
                      key={`cust-${cust.id}`}
                      onClick={() => {
                        onSelectCustomer(cust.id);
                        setIsOpen(false);
                        setQuery('');
                      }}
                      style={{
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#f8fafc')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <User size={15} style={{ color: '#6366f1' }} />
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 500, color: '#0f172a' }}>
                            {cust.name}
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            {cust.email} • Segment: {cust.segment} {cust.opted_out ? '• OPTED OUT' : ''}
                          </div>
                        </div>
                      </div>
                      <ArrowRight size={14} style={{ color: '#cbd5e1' }} />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
