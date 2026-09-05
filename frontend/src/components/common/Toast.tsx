import React from 'react';
import { CheckCircle, Info, AlertTriangle, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning';
  text: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 999,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        pointerEvents: 'none',
      }}
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{
            pointerEvents: 'auto',
            minWidth: '280px',
            maxWidth: '380px',
            padding: '12px 16px',
            borderRadius: 'var(--radius-md)',
            background: '#ffffff',
            border: '1px solid var(--neutral-border)',
            boxShadow: 'var(--shadow-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
            color: '#0f172a',
            animation: 'slideUp 0.2s ease-out',
          }}
        >
          {t.type === 'success' && <CheckCircle size={16} style={{ color: '#10b981', flexShrink: 0 }} />}
          {t.type === 'info' && <Info size={16} style={{ color: '#3b82f6', flexShrink: 0 }} />}
          {t.type === 'warning' && <AlertTriangle size={16} style={{ color: '#f59e0b', flexShrink: 0 }} />}
          
          <span style={{ flex: 1 }}>{t.text}</span>
          
          <button
            onClick={() => onDismiss(t.id)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#94a3b8',
              padding: '2px',
              display: 'flex',
            }}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
};
