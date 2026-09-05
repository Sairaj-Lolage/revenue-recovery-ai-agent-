import React from 'react';
import { Inbox, AlertCircle, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div
      style={{
        padding: '48px 24px',
        textAlign: 'center',
        background: '#ffffff',
        border: '1px border var(--neutral-border)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: '#f1f5f9',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#64748b',
          marginBottom: '16px',
        }}
      >
        <Inbox size={24} />
      </div>
      <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a', marginBottom: '4px' }}>
        {title}
      </h3>
      <p style={{ fontSize: '13px', color: '#64748b', maxWidth: '380px', margin: '0 auto 16px' }}>
        {description}
      </p>
      {actionText && onAction && (
        <button className="btn btn-secondary btn-sm" onClick={onAction}>
          {actionText}
        </button>
      )}
    </div>
  );
};

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to load recovery data',
  description = 'Something went wrong while loading this information. Please verify system connectivity or try refreshing.',
  onRetry,
}) => {
  return (
    <div
      style={{
        padding: '32px 24px',
        background: '#fef2f2',
        border: '1px solid #fecaca',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '16px',
      }}
    >
      <div style={{ color: '#dc2626', marginTop: '2px' }}>
        <AlertCircle size={20} />
      </div>
      <div style={{ flex: 1 }}>
        <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#991b1b', marginBottom: '4px' }}>
          {title}
        </h4>
        <p style={{ fontSize: '13px', color: '#7f1d1d', marginBottom: '12px' }}>
          {description}
        </p>
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry} style={{ borderColor: '#fca5a5' }}>
            <RefreshCw size={13} style={{ marginRight: '4px' }} />
            Try again
          </button>
        )}
      </div>
    </div>
  );
};
