import React, { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

type TimeRange = 'today' | '7d' | '30d';

const MOCK_TIME_DATA: Record<TimeRange, Array<{ name: string; failed: number; recovered: number; outstanding: number }>> = {
  today: [
    { name: '00:00', failed: 4500, recovered: 3200, outstanding: 1300 },
    { name: '04:00', failed: 2100, recovered: 1500, outstanding: 600 },
    { name: '08:00', failed: 8900, recovered: 5400, outstanding: 3500 },
    { name: '12:00', failed: 12400, recovered: 8900, outstanding: 3500 },
    { name: '16:00', failed: 6800, recovered: 5100, outstanding: 1700 },
    { name: '20:00', failed: 2095, recovered: 1420, outstanding: 675 },
  ],
  '7d': [
    { name: 'Mon', failed: 18500, recovered: 13200, outstanding: 5300 },
    { name: 'Tue', failed: 24200, recovered: 17800, outstanding: 6400 },
    { name: 'Wed', failed: 19800, recovered: 14500, outstanding: 5300 },
    { name: 'Thu', failed: 31000, recovered: 22400, outstanding: 8600 },
    { name: 'Fri', failed: 27500, recovered: 20100, outstanding: 7400 },
    { name: 'Sat', failed: 14200, recovered: 10800, outstanding: 3400 },
    { name: 'Sun', failed: 12900, recovered: 9800, outstanding: 3100 },
  ],
  '30d': [
    { name: 'Week 1', failed: 84000, recovered: 61000, outstanding: 23000 },
    { name: 'Week 2', failed: 96000, recovered: 71000, outstanding: 25000 },
    { name: 'Week 3', failed: 110000, recovered: 82000, outstanding: 28000 },
    { name: 'Week 4', failed: 104000, recovered: 78000, outstanding: 26000 },
  ],
};

export const PerformanceChart: React.FC = () => {
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const data = MOCK_TIME_DATA[timeRange];

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Recovery Performance</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Compare failed amounts vs AI-recovered and outstanding revenue (in INR)
          </p>
        </div>

        {/* Time range selector */}
        <div
          style={{
            display: 'inline-flex',
            background: '#f1f5f9',
            padding: '3px',
            borderRadius: 'var(--radius-sm)',
            gap: '2px',
          }}
        >
          {(['today', '7d', '30d'] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              style={{
                border: 'none',
                background: timeRange === r ? '#ffffff' : 'transparent',
                color: timeRange === r ? '#0f172a' : '#64748b',
                fontWeight: timeRange === r ? 600 : 500,
                fontSize: '12px',
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
                boxShadow: timeRange === r ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                textTransform: 'capitalize',
              }}
            >
              {r === 'today' ? 'Today' : r === '7d' ? '7 Days' : '30 Days'}
            </button>
          ))}
        </div>
      </div>

      <div style={{ width: '100%', height: 260, marginTop: '12px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} />
            <YAxis
              stroke="#94a3b8"
              fontSize={12}
              tickLine={false}
              tickFormatter={(val) => `₹${val.toLocaleString()}`}
            />
            <Tooltip
              formatter={(value: any) => [`₹${Number(value).toLocaleString()}`, '']}
              contentStyle={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Area
              type="monotone"
              dataKey="failed"
              name="Failed Amount"
              stroke="#ef4444"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorFailed)"
            />
            <Area
              type="monotone"
              dataKey="recovered"
              name="Recovered Amount"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorRecovered)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
