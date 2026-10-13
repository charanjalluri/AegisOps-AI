import React from 'react';
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  Clock,
  HelpCircle,
  RefreshCw,
  Server,
  X,
} from 'lucide-react';
import { ObservabilityStatus, ServiceHealthItem, ServiceHealthStatus } from '../types/api';

interface ObservabilityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  observability: ObservabilityStatus | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const ObservabilityDrawer: React.FC<ObservabilityDrawerProps> = ({
  isOpen,
  onClose,
  observability,
  onRefresh,
  isRefreshing,
}) => {
  if (!isOpen) return null;

  const renderStatusBadge = (status: ServiceHealthStatus) => {
    switch (status) {
      case 'healthy':
        return (
          <span className="badge badge-healthy">
            <CheckCircle2 size={12} /> Healthy
          </span>
        );
      case 'unhealthy':
        return (
          <span className="badge badge-unhealthy">
            <AlertOctagon size={12} /> Unhealthy
          </span>
        );
      case 'stale':
        return (
          <span className="badge badge-stale">
            <Clock size={12} /> Stale
          </span>
        );
      case 'unknown':
      default:
        return (
          <span className="badge badge-unknown">
            <HelpCircle size={12} /> Unknown
          </span>
        );
    }
  };

  const getLatencyBadge = (latencyMs: number, status: ServiceHealthStatus) => {
    if (status !== 'healthy') return null;
    const color = latencyMs < 100 ? '#4ade80' : latencyMs < 500 ? '#fbbf24' : '#f87171';
    return (
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          color,
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
          padding: '2px 6px',
          borderRadius: '4px',
          border: '1px solid #1e293b',
        }}
      >
        {latencyMs.toFixed(1)}ms
      </span>
    );
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 100,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '520px',
          height: '100%',
          backgroundColor: '#090d16',
          borderLeft: '1px solid #1e293b',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-8px 0 24px rgba(0, 0, 0, 0.8)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} color="#38bdf8" />
              <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                Platform Health & Service Mesh
              </h2>
            </div>
            <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
              Active socket probing distinguishing Healthy, Unhealthy, Unknown, and Stale
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* System Summary Banner */}
        {observability && (
          <div
            style={{
              padding: '16px 24px',
              backgroundColor: '#020617',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>
                Aggregate Availability
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                {observability.healthy_count} of {observability.total_count} Monitored Services Responsive
              </div>
            </div>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#1e293b',
                color: '#38bdf8',
                border: '1px solid #334155',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: isRefreshing ? 'wait' : 'pointer',
              }}
            >
              <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
              Re-probe Services
            </button>
          </div>
        )}

        {/* Services List Scroll Area */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {!observability ? (
            <div style={{ padding: '32px 0', textAlign: 'center', color: '#64748b' }}>
              Probing infrastructure endpoints...
            </div>
          ) : (
            observability.services.map((svc: ServiceHealthItem) => (
              <div
                key={svc.service}
                style={{
                  backgroundColor: '#020617',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '12px 16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Server size={14} color="#38bdf8" />
                    <span style={{ fontWeight: 600, fontSize: '13px', color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                      {svc.service}
                    </span>
                    <span
                      style={{
                        fontSize: '11px',
                        color: '#64748b',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      :{svc.port}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {getLatencyBadge(svc.latency_ms, svc.status)}
                    {renderStatusBadge(svc.status)}
                  </div>
                </div>

                {svc.details && (
                  <div style={{ fontSize: '11px', color: '#94a3b8', lineHeight: '1.4' }}>
                    {svc.details}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
