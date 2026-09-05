import React from 'react';
import { 
  CheckCircle2, 
  Clock, 
  XCircle, 
  ShieldAlert, 
  Ban, 
  Activity
} from 'lucide-react';
import type { CaseStatus, PaymentStatus } from '../../types';

interface BadgeProps {
  status: CaseStatus | PaymentStatus | 'active' | 'opted_out' | string;
  label?: string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ status, label }) => {
  const norm = status.toUpperCase();

  if (norm === 'RECOVERED' || norm === 'SUCCESS' || norm === 'ACTIVE') {
    return (
      <span className="badge badge-success">
        <CheckCircle2 size={12} className="text-emerald-600" />
        <span>{label || (norm === 'SUCCESS' ? 'Success' : norm === 'RECOVERED' ? 'Recovered' : 'Active')}</span>
      </span>
    );
  }

  if (norm === 'IN_PROGRESS' || norm === 'PENDING') {
    return (
      <span className="badge badge-warning">
        <Clock size={12} className="text-amber-600" />
        <span>{label || (norm === 'PENDING' ? 'Pending' : 'In Progress')}</span>
      </span>
    );
  }

  if (norm === 'FAILED' || norm === 'FAILURE') {
    return (
      <span className="badge badge-danger">
        <XCircle size={12} className="text-red-600" />
        <span>{label || 'Failed'}</span>
      </span>
    );
  }

  if (norm === 'ESCALATED') {
    return (
      <span className="badge badge-danger">
        <ShieldAlert size={12} className="text-red-600" />
        <span>{label || 'Escalated'}</span>
      </span>
    );
  }

  if (norm === 'STOPPED' || norm === 'OPTED_OUT') {
    return (
      <span className="badge badge-neutral">
        <Ban size={12} className="text-slate-500" />
        <span>{label || (norm === 'OPTED_OUT' ? 'Opted Out' : 'Stopped')}</span>
      </span>
    );
  }

  if (norm === 'OPEN') {
    return (
      <span className="badge badge-primary">
        <Activity size={12} className="text-blue-600" />
        <span>{label || 'Open'}</span>
      </span>
    );
  }

  return (
    <span className="badge badge-neutral">
      <span>{label || status}</span>
    </span>
  );
};
