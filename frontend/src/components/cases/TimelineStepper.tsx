import React from 'react';
import { Bot, Shield, Wrench, User, AlertOctagon } from 'lucide-react';
import type { TimelineEvent } from '../../types';

interface TimelineStepperProps {
  events: TimelineEvent[];
}

export const TimelineStepper: React.FC<TimelineStepperProps> = ({ events }) => {
  const getEventBadge = (type: TimelineEvent['type']) => {
    switch (type) {
      case 'agent':
        return { icon: Bot, bg: '#dbeafe', color: '#1d4ed8', label: 'Agent Decision' };
      case 'guardrail':
        return { icon: Shield, bg: '#fef3c7', color: '#b45309', label: 'Policy Check' };
      case 'tool':
        return { icon: Wrench, bg: '#e0e7ff', color: '#4338ca', label: 'Tool Executed' };
      case 'customer':
        return { icon: User, bg: '#ecfdf5', color: '#047857', label: 'Customer Action' };
      default:
        return { icon: AlertOctagon, bg: '#fee2e2', color: '#b91c1c', label: 'System Event' };
    }
  };

  return (
    <div style={{ padding: '8px 0', position: 'relative' }}>
      {/* Vertical line connecting events */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          bottom: '20px',
          left: '15px',
          width: '2px',
          background: '#e2e8f0',
          zIndex: 1,
        }}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', position: 'relative', zIndex: 2 }}>
        {events.map((ev, index) => {
          const info = getEventBadge(ev.type);
          const Icon = info.icon;
          const isLast = index === events.length - 1;

          return (
            <div key={ev.id} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
              {/* Event Icon Bubble */}
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: info.bg,
                  color: info.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  boxShadow: '0 0 0 3px #ffffff',
                }}
              >
                <Icon size={16} />
              </div>

              {/* Event Content Box */}
              <div
                style={{
                  flex: 1,
                  background: isLast ? '#f8fafc' : '#ffffff',
                  border: `1px solid ${isLast ? '#cbd5e1' : '#e2e8f0'}`,
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
                      {ev.title}
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: info.bg,
                        color: info.color,
                        textTransform: 'uppercase',
                      }}
                    >
                      {info.label}
                    </span>
                  </div>

                  <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
                    {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: '#475569', margin: 0 }}>
                  {ev.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
