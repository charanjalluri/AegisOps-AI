import React from 'react';
import {
  Activity,
  AlertCircle,
  RefreshCw,
  Shield,
  User,
} from 'lucide-react';
import { ObservabilityStatus } from '../types/api';

interface HeaderProps {
  observability: ObservabilityStatus | null;
  activeIncidentCount: number;
  onOpenObservability: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  operatorId: string;
  operatorRole: string;
}

export const Header: React.FC<HeaderProps> = ({
  observability,
  activeIncidentCount,
  onOpenObservability,
  onRefresh,
  isRefreshing,
  operatorId,
  operatorRole,
}) => {
  const getHealthBadge = () => {
    if (!observability) {
      return (
        <span className="badge badge-unknown">
          <Activity size={12} /> Probing System...
        </span>
      );
    }

    if (observability.overall_status === 'healthy') {
      return (
        <button
          onClick={onOpenObservability}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(34, 197, 94, 0.12)',
            color: '#4ade80',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            borderRadius: '9999px',
            padding: '4px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
          title="Click to view full observability telemetry"
        >
          <span className="pulse-dot" style={{ backgroundColor: '#22c55e' }} />
          <span>Platform Healthy ({observability.healthy_count}/{observability.total_count})</span>
        </button>
      );
    }

    if (observability.overall_status === 'degraded') {
      return (
        <button
          onClick={onOpenObservability}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(245, 158, 11, 0.12)',
            color: '#fbbf24',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            borderRadius: '9999px',
            padding: '4px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
          title="Click to inspect degraded services"
        >
          <AlertCircle size={14} color="#f59e0b" />
          <span>System Degraded ({observability.healthy_count}/{observability.total_count})</span>
        </button>
      );
    }

    return (
      <button
        onClick={onOpenObservability}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(239, 68, 68, 0.15)',
          color: '#f87171',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '9999px',
          padding: '4px 12px',
          fontSize: '12px',
          fontWeight: 600,
          cursor: 'pointer',
        }}
        title="Critical outages detected across services"
      >
        <span className="pulse-dot" style={{ backgroundColor: '#ef4444' }} />
        <span>Platform Outage ({observability.healthy_count}/{observability.total_count})</span>
      </button>
    );
  };

  return (
    <header
      style={{
        height: '64px',
        backgroundColor: '#020617',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        zIndex: 50,
      }}
    >
      {/* Left: Brand Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              backgroundColor: '#0f172a',
              border: '1px solid #38bdf8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.25)',
            }}
          >
            <Shield size={20} color="#38bdf8" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 700, fontSize: '16px', color: '#f8fafc', letterSpacing: '-0.02em' }}>
                AegisOps AI
              </span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  textTransform: 'uppercase',
                }}
              >
                Ops Cockpit
              </span>
            </div>
            <span style={{ fontSize: '11px', color: '#64748b' }}>Autonomous SRE Incident Operations</span>
          </div>
        </div>

        <div style={{ height: '24px', width: '1px', backgroundColor: '#1e293b', margin: '0 4px' }} />

        {/* System Health Button */}
        {getHealthBadge()}
      </div>

      {/* Right: Controls & Operator Session */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Active Incidents Counter */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            padding: '4px 12px',
            borderRadius: '8px',
            fontSize: '12px',
          }}
        >
          <span style={{ color: '#94a3b8' }}>Active Incidents:</span>
          <span
            style={{
              fontWeight: 700,
              color: activeIncidentCount > 0 ? '#f87171' : '#4ade80',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {activeIncidentCount}
          </span>
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            color: '#94a3b8',
            padding: '6px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            cursor: isRefreshing ? 'wait' : 'pointer',
          }}
          title="Refresh active incidents and platform observability"
        >
          <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>

        {/* Operator Profile Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#0f172a',
            border: '1px solid #334155',
            padding: '4px 12px',
            borderRadius: '9999px',
            fontSize: '12px',
          }}
        >
          <User size={13} color="#38bdf8" />
          <span style={{ color: '#f8fafc', fontWeight: 500 }}>{operatorId}</span>
          <span
            style={{
              backgroundColor: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
              fontSize: '10px',
              fontWeight: 700,
              padding: '1px 6px',
              borderRadius: '4px',
              textTransform: 'uppercase',
            }}
          >
            {operatorRole}
          </span>
        </div>
      </div>
    </header>
  );
};
