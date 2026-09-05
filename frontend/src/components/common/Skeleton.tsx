import React from 'react';

export const KPISkeleton: React.FC = () => (
  <div className="card" style={{ height: '110px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ height: '14px', width: '90px', background: '#e2e8f0', borderRadius: '4px' }} />
      <div style={{ height: '28px', width: '28px', background: '#e2e8f0', borderRadius: '50%' }} />
    </div>
    <div style={{ height: '24px', width: '120px', background: '#cbd5e1', borderRadius: '4px' }} />
    <div style={{ height: '12px', width: '80px', background: '#e2e8f0', borderRadius: '4px' }} />
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="table-wrapper">
    <table className="data-table">
      <thead>
        <tr>
          {Array.from({ length: 6 }).map((_, i) => (
            <th key={i}>
              <div style={{ height: '12px', width: '70%', background: '#e2e8f0', borderRadius: '4px' }} />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <tr key={rowIndex}>
            {Array.from({ length: 6 }).map((_, colIndex) => (
              <td key={colIndex}>
                <div style={{ height: '14px', width: colIndex === 0 ? '40%' : '80%', background: '#f1f5f9', borderRadius: '4px' }} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export const TimelineSkeleton: React.FC = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '12px 0' }}>
    {Array.from({ length: 4 }).map((_, i) => (
      <div key={i} style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#cbd5e1' }} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ height: '14px', width: '40%', background: '#e2e8f0', borderRadius: '4px' }} />
          <div style={{ height: '12px', width: '70%', background: '#f1f5f9', borderRadius: '4px' }} />
        </div>
      </div>
    ))}
  </div>
);
