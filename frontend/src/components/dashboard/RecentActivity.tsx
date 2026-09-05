import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import type { AuditLog } from '../../types';

interface RecentActivityProps {
  auditLogs: AuditLog[];
  onSelectCase: (caseId: number) => void;
}

export const RecentActivity: React.FC<RecentActivityProps> = ({ auditLogs, onSelectCase }) => {
  const recentLogs = auditLogs.slice(0, 6);

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Recent Recovery Activity</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Real-time feed of automated actions & system events
          </p>
        </div>
      </div>

      <div className="table-wrapper" style={{ border: 'none' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '80px' }}>Time</th>
              <th style={{ width: '100px' }}>Payment</th>
              <th>Event / Activity</th>
              <th style={{ width: '90px' }}>Actor</th>
              <th style={{ width: '80px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {recentLogs.map((log) => (
              <tr key={log.id}>
                <td style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                  {formatTime(log.timestamp)}
                </td>
                <td style={{ fontWeight: 600 }}>Payment #{log.payment_id}</td>
                <td>
                  <div style={{ fontSize: '13px', color: '#0f172a', fontWeight: 500 }}>
                    {log.event_type.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    {log.details}
                  </div>
                </td>
                <td>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: log.actor === 'agent' ? '#dbeafe' : log.actor === 'guardrail' ? '#fef3c7' : '#f1f5f9',
                      color: log.actor === 'agent' ? '#1e40af' : log.actor === 'guardrail' ? '#92400e' : '#334155',
                      fontWeight: 600,
                      textTransform: 'capitalize',
                    }}
                  >
                    {log.actor}
                  </span>
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
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
