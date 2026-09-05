import React, { useEffect, useState, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import type { NavTab } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { DashboardPage } from './pages/DashboardPage';
import { PaymentsPage } from './pages/PaymentsPage';
import { RecoveryCasesPage } from './pages/RecoveryCasesPage';
import { CustomersPage } from './pages/CustomersPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { SettingsPage } from './pages/SettingsPage';
import { CaseDetailDrawer } from './components/cases/CaseDetailDrawer';
import { CustomerDetailDrawer } from './components/customers/CustomerDetailDrawer';
import { ToastContainer } from './components/common/Toast';
import type { ToastMessage } from './components/common/Toast';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import {
  fetchPayments,
  fetchRecoveryCases,
  fetchCustomers,
  fetchAuditLogs,
  fetchDashboardStats,
  triggerPaymentFailed,
} from './api';
import type { Customer, Payment, RecoveryCase, AuditLog, DashboardKPIS } from './types';
import { formatINR } from './utils/formatters';

const DEFAULT_KPIS: DashboardKPIS = {
  amountAtRiskPaise: 0,
  recoveredAmountPaise: 0,
  failedCount: 0,
  recoveryRatePercent: 0.0,
  inProgressCount: 0,
  escalatedCount: 0,
  stoppedCount: 0,
  totalRecoveriesToday: 0,
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Real Backend Data States
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [kpis, setKpis] = useState<DashboardKPIS>(DEFAULT_KPIS);

  // Status & UI States
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Active Drawer States
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);

  // Toast Helper
  const addToast = useCallback((text: string, type: 'success' | 'info' | 'warning' = 'info') => {
    const id = Date.now().toString() + Math.random().toString().slice(2, 5);
    const newToast: ToastMessage = { id, text, type };
    setToasts((prev) => [...prev, newToast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Main Data Fetcher
  const loadAppData = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setIsRefreshing(true);
    try {
      const [pData, cData, custData, logsData, statsData] = await Promise.all([
        fetchPayments(),
        fetchRecoveryCases(),
        fetchCustomers(),
        fetchAuditLogs(),
        fetchDashboardStats(),
      ]);

      setPayments(pData);
      setCases(cData);
      setCustomers(custData);
      setAuditLogs(logsData);
      setKpis(statsData);
      setBackendUnavailable(false);

      if (isManualRefresh) {
        addToast('Dashboard reloaded with latest backend state.', 'success');
      }
    } catch (err: any) {
      console.error('Failed to load application data from FastAPI backend:', err);
      setBackendUnavailable(true);
      addToast('Backend service is unreachable. Make sure FastAPI server is running on http://127.0.0.1:8000.', 'warning');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadAppData();
  }, [loadAppData]);

  // Handler for direct simulation of recovery on any payment
  const handleSimulatePaymentRecovery = async (paymentId: number) => {
    try {
      addToast(`Triggering AI Recovery Agent workflow for Payment #${paymentId}...`, 'info');
      const res = await triggerPaymentFailed(paymentId);
      
      const recRes = res.recovery_result || {};
      const statusStr = recRes.final_status;
      const recoveredPaise = recRes.amount_recovered_paise || 0;

      if (statusStr === 'success') {
        addToast(`Payment #${paymentId} recovered! ${formatINR(recoveredPaise)} recovered via automatic retry.`, 'success');
      } else if (statusStr === 'stopped') {
        addToast(`Recovery stopped for Payment #${paymentId}. Customer opted out or policy blocked.`, 'warning');
      } else if (statusStr === 'escalated') {
        addToast(`Recovery escalated for Payment #${paymentId}. Case sent to manual human intervention queue.`, 'warning');
      } else {
        addToast(`Payment failure ingested. AI Recovery started for Payment #${paymentId}.`, 'info');
      }

      await loadAppData();
    } catch (err: any) {
      addToast(`Simulation error: ${err.message}`, 'warning');
    }
  };

  const selectedCustomer = customers.find((c) => c.id === selectedCustomerId) || null;
  const inProgressCasesCount = cases.filter((c) => c.status === 'IN_PROGRESS').length;

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        inProgressCasesCount={inProgressCasesCount}
      />

      {/* Main Content Area */}
      <div className="main-content">
        <Header
          payments={payments}
          cases={cases}
          customers={customers}
          onSelectPayment={(id) => {
            const p = payments.find((x) => x.id === id);
            const caseId = p?.case_id || p?.recovery_case_id;
            if (caseId) setSelectedCaseId(caseId);
            else handleSimulatePaymentRecovery(id);
          }}
          onSelectCase={(id) => setSelectedCaseId(id)}
          onSelectCustomer={(id) => setSelectedCustomerId(id)}
          onRefresh={() => loadAppData(true)}
          onSimulateAction={() => {
            const failedP = payments.find((p) => p.status === 'failed' && !p.case_id);
            const targetId = failedP ? failedP.id : (payments[0]?.id || 67);
            handleSimulatePaymentRecovery(targetId);
          }}
          isRefreshing={isRefreshing}
        />

        <main className="page-body">
          {/* Backend Connection Failure Alert Banner */}
          {backendUnavailable && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: 'var(--radius-md)',
                padding: '16px 20px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#991b1b',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <AlertTriangle size={20} style={{ color: '#dc2626' }} />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>Backend Unreachable</div>
                  <div style={{ fontSize: '12px', color: '#b91c1c' }}>
                    Unable to connect to the FastAPI recovery service at <code>http://127.0.0.1:8000</code>. Please ensure the backend server is running.
                  </div>
                </div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => loadAppData(true)}>
                <RefreshCw size={14} className={isRefreshing ? 'spin-icon' : ''} />
                <span>Retry Connection</span>
              </button>
            </div>
          )}

          {/* Loading Skeleton View */}
          {isLoading ? (
            <div style={{ padding: '60px 0', textAlign: 'center', color: '#64748b' }}>
              <RefreshCw size={28} className="spin-icon" style={{ marginBottom: '12px', color: '#2563eb' }} />
              <div style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a' }}>Connecting to AI Recovery Agent Backend...</div>
              <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>Loading payments, recovery cases, and customer history</div>
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <DashboardPage
                  kpis={kpis}
                  cases={cases}
                  auditLogs={auditLogs}
                  onSelectCase={(id) => setSelectedCaseId(id)}
                  onNavigateToTab={(tab) => setActiveTab(tab)}
                />
              )}

              {activeTab === 'payments' && (
                <PaymentsPage
                  payments={payments}
                  onSelectPayment={(id) => {
                    const p = payments.find((x) => x.id === id);
                    const cId = p?.case_id || p?.recovery_case_id;
                    if (cId) setSelectedCaseId(cId);
                  }}
                  onSelectCase={(id) => setSelectedCaseId(id)}
                  onSimulateRecovery={handleSimulatePaymentRecovery}
                />
              )}

              {activeTab === 'cases' && (
                <RecoveryCasesPage
                  cases={cases}
                  onSelectCase={(id) => setSelectedCaseId(id)}
                />
              )}

              {activeTab === 'customers' && (
                <CustomersPage
                  customers={customers}
                  onSelectCustomer={(id) => setSelectedCustomerId(id)}
                />
              )}

              {activeTab === 'audit' && (
                <AuditLogsPage
                  auditLogs={auditLogs}
                  onSelectCase={(id) => setSelectedCaseId(id)}
                />
              )}

              {activeTab === 'settings' && (
                <SettingsPage
                  onTriggerToast={addToast}
                  onRefreshData={() => loadAppData(true)}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Case Detail Side Drawer */}
      <CaseDetailDrawer
        caseId={selectedCaseId}
        onClose={() => setSelectedCaseId(null)}
        onRefreshData={() => loadAppData(false)}
        onShowToast={addToast}
      />

      {/* Customer Detail Side Drawer */}
      <CustomerDetailDrawer
        customer={selectedCustomer}
        payments={payments}
        cases={cases}
        onClose={() => setSelectedCustomerId(null)}
        onSelectCase={(id) => {
          setSelectedCustomerId(null);
          setSelectedCaseId(id);
        }}
      />

      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
};

export default App;
