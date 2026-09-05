import React, { useState } from 'react';
import { Search, Activity, ArrowUpRight } from 'lucide-react';
import type { AuditLog, AuditActor } from '../types';
import { formatTimestamp } from '../utils/formatters';
import { EmptyState } from '../components/common/EmptyState';

interface AuditLogsPageProps {
  auditLogs: AuditLog[];
  onSelectCase: (caseId: number) => void;
}

export const AuditLogsPage: React.FC<AuditLogsPageProps> = ({ auditLogs, onSelectCase }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [actorFilter, setActorFilter] = useState<string>('ALL');

  const filteredLogs = auditLogs.filter((log) => {
    const matchesSearch =
      searchTerm === '' ||
      log.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.details.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.payment_id && log.payment_id.toString().includes(searchTerm)) ||
      log.recovery_case_id.toString().includes(searchTerm);

    const matchesActor = actorFilter === 'ALL' || log.actor === actorFilter;

    return matchesSearch && matchesActor;
  });

  const getActorBadge = (actor: AuditActor) => {
    switch (actor) {
      case 'agent':
        return { bg: '#dbeafe', color: '#1e40af', label: 'Agent' };
      case 'guardrail':
        return { bg: '#fef3c7', color: '#92400e', label: 'Guardrail' };
      case 'tool':
        return { bg: '#e0e7ff', color: '#3730a3', label: 'Tool' };
      default:
        return { bg: '#f1f5f9', color: '#334155', label: 'System' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Page Header with Concept Distinction Note */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Activity / System Audit Stream</h1>
          <p className="page-subtitle">
            Complete event log trace representing the <strong>AuditLog</strong> concept.
          </p>
        </div>
      </div>

      {/* Info Callout explaining distinction */}
      <div
        style={{
          padding: '12px 16px',
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          fontSize: '13px',
          color: '#1e40af',
        }}
      >
        <Activity size={18} style={{ color: '#2563eb', flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong>Domain Concept Distinction:</strong>
          <span style={{ marginLeft: '4px' }}>
            <strong>Recovery Actions</strong> are high-level business operations (retries, links, messages).
            <strong> Audit Activity</strong> records the granular step-by-step system execution history (diagnosis, policy checks, tool invocations).
          </span>
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
            width: '320px',
          }}
        >
          <Search size={15} style={{ color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search events, details, payment #, case #..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: '13px', width: '100%' }}
          />
        </div>

        {/* Actor Filter Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {(['ALL', 'agent', 'guardrail', 'tool', 'system'] as const).map((act) => (
            <button
              key={act}
              onClick={() => setActorFilter(act)}
              style={{
                border: '1px solid',
                borderColor: actorFilter === act ? '#2563eb' : 'var(--neutral-border)',
                background: actorFilter === act ? '#eff6ff' : '#ffffff',
                color: actorFilter === act ? '#1d4ed8' : '#64748b',
                fontWeight: actorFilter === act ? 600 : 500,
                fontSize: '12px',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {act === 'ALL' ? 'All Actors' : act}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Log Table */}
      {filteredLogs.length === 0 ? (
        <EmptyState
          title="No audit events found"
          description="There are no log events matching the active query or actor filter."
          actionText="Clear Filters"
          onAction={() => {
            setSearchTerm('');
            setActorFilter('ALL');
          }}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '150px' }}>Timestamp</th>
                <th style={{ width: '160px' }}>Event Type</th>
                <th style={{ width: '100px' }}>Actor</th>
                <th style={{ width: '100px' }}>Payment</th>
                <th style={{ width: '90px' }}>Case</th>
                <th>Details</th>
                <th style={{ textAlign: 'right', width: '90px' }}>Investigate</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => {
                const actorInfo = getActorBadge(log.actor);
                return (
                  <tr key={log.id}>
                    <td style={{ fontSize: '12px', color: '#64748b', fontFamily: 'monospace' }}>
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, fontSize: '12px', color: '#0f172a', fontFamily: 'monospace' }}>
                        {log.event_type}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: actorInfo.bg,
                          color: actorInfo.color,
                          textTransform: 'capitalize',
                        }}
                      >
                        {log.actor}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#0f172a' }}>
                      Payment #{log.payment_id}
                    </td>
                    <td style={{ fontWeight: 600, color: '#2563eb' }}>
                      Case #{log.recovery_case_id}
                    </td>
                    <td style={{ fontSize: '12px', color: '#334155' }}>
                      {log.details}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => onSelectCase(log.recovery_case_id)}
                        style={{ padding: '2px 6px' }}
                      >
                        <ArrowUpRight size={13} />
                      </button>
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
