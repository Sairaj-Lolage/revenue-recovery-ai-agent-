import React from 'react';
import {
  LayoutDashboard,
  CreditCard,
  ShieldAlert,
  Users,
  Activity,
  Sliders,
  Bot,
  ChevronLeft,
  Menu,
} from 'lucide-react';

export type NavTab = 'dashboard' | 'payments' | 'cases' | 'customers' | 'audit' | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  inProgressCasesCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  collapsed,
  onToggleCollapse,
  inProgressCasesCount,
}) => {
  const navItems = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'payments' as NavTab, label: 'Payments', icon: CreditCard },
    {
      id: 'cases' as NavTab,
      label: 'Recovery Cases',
      icon: ShieldAlert,
      badge: inProgressCasesCount > 0 ? inProgressCasesCount : undefined,
    },
    { id: 'customers' as NavTab, label: 'Customers', icon: Users },
    { id: 'audit' as NavTab, label: 'Activity / Audit', icon: Activity },
    { id: 'settings' as NavTab, label: 'Settings', icon: Sliders },
  ];

  return (
    <aside
      style={{
        width: collapsed ? '70px' : '240px',
        minWidth: collapsed ? '70px' : '240px',
        background: '#ffffff',
        borderRight: '1px solid var(--neutral-border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        transition: 'all 0.2s ease-in-out',
        zIndex: 90,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '20px 16px',
          borderBottom: '1px solid var(--neutral-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
        }}
      >
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: 'linear-gradient(135deg, #2563eb, #1e3a8a)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 2px 4px rgba(37, 99, 235, 0.25)',
              }}
            >
              <Bot size={18} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a', lineHeight: 1.2 }}>
                Recovery Agent
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: '#10b981',
                    display: 'inline-block',
                  }}
                />
                Active Monitoring
              </div>
            </div>
          </div>
        )}

        {collapsed && (
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-sm)',
              background: 'linear-gradient(135deg, #2563eb, #1e3a8a)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            <Bot size={20} />
          </div>
        )}
      </div>

      {/* Navigation List */}
      <nav style={{ padding: '16px 8px', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                padding: collapsed ? '10px' : '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                background: isActive ? '#eff6ff' : 'transparent',
                color: isActive ? '#1d4ed8' : '#475569',
                fontWeight: isActive ? 600 : 500,
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                width: '100%',
                textAlign: 'left',
              }}
              title={collapsed ? item.label : undefined}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Icon size={18} style={{ color: isActive ? '#2563eb' : '#64748b' }} />
                {!collapsed && <span>{item.label}</span>}
              </div>

              {!collapsed && item.badge && (
                <span
                  style={{
                    background: '#fee2e2',
                    color: '#dc2626',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: '10px',
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Collapse button */}
      <div style={{ padding: '12px', borderTop: '1px solid var(--neutral-border)' }}>
        <button
          onClick={onToggleCollapse}
          className="btn btn-outline"
          style={{ width: '100%', justifyContent: collapsed ? 'center' : 'flex-start', padding: '6px' }}
        >
          {collapsed ? <Menu size={16} /> : <><ChevronLeft size={16} /> Collapse menu</>}
        </button>
      </div>
    </aside>
  );
};
