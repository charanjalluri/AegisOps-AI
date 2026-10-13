import React from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { VerificationStatus } from '../../types/api';

interface RemediationVerificationWidgetProps {
  status: VerificationStatus;
  incidentId: string;
  onTriggerVerification: () => Promise<void>;
  isVerifying: boolean;
}

export const RemediationVerificationWidget: React.FC<RemediationVerificationWidgetProps> = ({
  status,
  incidentId,
  onTriggerVerification,
  isVerifying,
}) => {
  const isVerified = status.status === 'verified';
  const isFailed = status.status === 'failed' || status.status === 'escalated';
  const passPercent = Math.min(100, Math.round((status.consecutive_passes / Math.max(1, status.target_passes)) * 100));

  return (
    <div
      style={{
        backgroundColor: '#090d16',
        border: isVerified ? '1px solid #22c55e' : isFailed ? '1px solid #ef4444' : '1px solid #38bdf8',
        borderRadius: '10px',
        padding: '20px',
        boxShadow: isVerified ? '0 0 16px rgba(34, 197, 94, 0.15)' : 'none',
      }}
    >
      {/* Header Banner */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={16} color={isVerified ? '#4ade80' : isFailed ? '#f87171' : '#38bdf8'} />
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Closed-Loop Telemetry Verification Loop (GOV-03)
          </h3>
          <span style={{ fontSize: '11px', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
            ({incidentId})
          </span>
        </div>

        <div>
          {isVerified ? (
            <span className="badge badge-healthy">
              <CheckCircle2 size={11} /> Verified Recovered
            </span>
          ) : isFailed ? (
            <span className="badge badge-critical">
              <AlertTriangle size={11} /> Threshold Exceeded (Escalated)
            </span>
          ) : (
            <span className="badge badge-medium">
              <Clock size={11} /> Polling Stabilization...
            </span>
          )}
        </div>
      </div>

      {/* Backend Decision Banner */}
      {isVerified && (
        <div
          style={{
            backgroundColor: 'rgba(34, 197, 94, 0.12)',
            border: '1px solid rgba(34, 197, 94, 0.35)',
            borderRadius: '8px',
            padding: '14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <ShieldCheck size={24} color="#4ade80" />
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
              Remediation Verified by Closed-Loop Engine
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
              Operational error rate and connection pool metrics met sustained recovery thresholds across consecutive polling windows. Incident marked resolved.
            </div>
          </div>
        </div>
      )}

      {isFailed && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '8px',
            padding: '14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <ShieldAlert size={24} color="#f87171" />
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
              Verification Failed — Escalation Triggered
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
              Telemetry did not stabilize within configured recovery window. Escalation webhook dispatched to on-call paging channel.
            </div>
          </div>
        </div>
      )}

      {/* Threshold Condition Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '16px' }}>
        {status.conditions.map((cond) => (
          <div
            key={cond.metric_name}
            style={{
              backgroundColor: '#020617',
              border: '1px solid #1e293b',
              borderRadius: '6px',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>
              Threshold Target: {cond.metric_name}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
              {cond.metric_name} {cond.operator} {cond.threshold} ({cond.unit})
            </div>
          </div>
        ))}

        {/* Consecutive Success Progress */}
        <div
          style={{
            backgroundColor: '#020617',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
            <span>Consecutive Passes</span>
            <span style={{ fontWeight: 700, color: '#f8fafc' }}>
              {status.consecutive_passes} / {status.target_passes} Required
            </span>
          </div>

          <div
            style={{
              height: '6px',
              backgroundColor: '#1e293b',
              borderRadius: '3px',
              marginTop: '8px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${passPercent}%`,
                height: '100%',
                backgroundColor: isVerified ? '#22c55e' : '#38bdf8',
                transition: 'width 0.4s ease',
              }}
            />
          </div>
        </div>
      </div>

      {/* Telemetry Samples Table */}
      {status.samples && status.samples.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '6px' }}>
            Backend Metric Polling Samples
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {status.samples.map((sample, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: '#020617',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: sample.passed ? '#22c55e' : '#ef4444',
                    }}
                  />
                  <span style={{ fontFamily: 'var(--font-mono)', color: '#f8fafc' }}>
                    {sample.metric_name}
                  </span>
                  <span style={{ color: '#64748b' }}>=</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: sample.passed ? '#4ade80' : '#f87171' }}>
                    {sample.value}
                  </span>
                </div>

                <span style={{ color: '#64748b', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                  {new Date(sample.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trigger Verification Action Button */}
      {!isVerified && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #1e293b', paddingTop: '12px' }}>
          <button
            onClick={onTriggerVerification}
            disabled={isVerifying}
            style={{
              backgroundColor: '#1e293b',
              color: '#38bdf8',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: isVerifying ? 'wait' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <RefreshCw size={12} className={isVerifying ? 'animate-spin' : ''} />
            <span>Poll Verification Loop</span>
          </button>
        </div>
      )}
    </div>
  );
};
