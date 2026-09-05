import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string;
  subtext: string;
  icon: LucideIcon;
  colorType?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
  onClick?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtext,
  icon: Icon,
  colorType = 'neutral',
  onClick,
}) => {
  const colorMap = {
    primary: { iconBg: '#eff6ff', iconColor: '#2563eb' },
    success: { iconBg: '#ecfdf5', iconColor: '#10b981' },
    warning: { iconBg: '#fffbeb', iconColor: '#f59e0b' },
    danger: { iconBg: '#fef2f2', iconColor: '#ef4444' },
    neutral: { iconBg: '#f1f5f9', iconColor: '#64748b' },
  };

  const currentTheme = colorMap[colorType];

  return (
    <div
      className="card"
      onClick={onClick}
      style={{
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          e.currentTarget.style.transform = 'none';
          e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        }
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>
          {title}
        </span>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-sm)',
            background: currentTheme.iconBg,
            color: currentTheme.iconColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon size={18} />
        </div>
      </div>

      <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.02em', marginBottom: '4px' }}>
        {value}
      </div>

      <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <span>{subtext}</span>
      </div>
    </div>
  );
};
