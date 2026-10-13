import React, { useState } from 'react';
import {
  AlertOctagon,
  CheckCircle2,
  Clock,
  RotateCcw,
  ShieldAlert,
  User,
  XCircle,
} from 'lucide-react';
import { ActionProposal } from '../../types/api';

interface HumanApprovalCardProps {
  proposal: ActionProposal;
  operatorId: string;
  operatorRole: string;
  onApprove: (proposalId: string, comment?: string) => Promise<void>;
  onReject: (proposalId: string, reason: string) => Promise<void>;
  onExecute: (proposalId: string) => Promise<void>;
  isMutating: boolean;
}

export const HumanApprovalCard: React.FC<HumanApprovalCardProps> = ({
  proposal,
  operatorId,
  operatorRole,
  onApprove,
  onReject,
  onExecute,
  isMutating,
}) => {
  const [comment, setComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleApprove = async () => {
    setActionError(null);
    try {
      await onApprove(proposal.id, comment.trim() || undefined);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setActionError('A rejection explanation is mandatory for audit accountability.');
      return;
    }
    setActionError(null);
    try {
      await onReject(proposal.id, rejectReason.trim());
      setShowRejectInput(false);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleExecute = async () => {
    setActionError(null);
    try {
      await onExecute(proposal.id);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : String(err));
    }
  };

  const isApproved = proposal.status === 'approved';
  const isExecuted = proposal.status === 'executed' || proposal.status === 'verified';
  const isRejected = proposal.status === 'rejected';
  const isExpired = proposal.status === 'expired';

  return (
    <div
      style={{
        backgroundColor: '#090d16',
        border: isExecuted ? '1px solid #22c55e' : isApproved ? '1px solid #38bdf8' : '1px solid #ef4444',
        borderRadius: '10px',
        padding: '20px',
        boxShadow: isApproved ? '0 0 16px rgba(56, 189, 248, 0.15)' : 'none',
      }}
    >
      {/* Top Banner: Risk Level and Action Type */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-critical" style={{ fontSize: '11px', padding: '3px 10px' }}>
            <ShieldAlert size={12} /> {proposal.risk_level} RISK MUTATION
          </span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              fontWeight: 700,
              color: '#f8fafc',
            }}
          >
            {proposal.action_type}
          </span>
        </div>

        {/* State Badge */}
        <div>
          {isExecuted ? (
            <span className="badge badge-healthy">
              <CheckCircle2 size={11} /> Executed & Active
            </span>
          ) : isApproved ? (
            <span className="badge badge-medium">
              <CheckCircle2 size={11} /> Approved by Operator
            </span>
          ) : isRejected ? (
            <span className="badge badge-critical">
              <XCircle size={11} /> Rejected
            </span>
          ) : isExpired ? (
            <span className="badge badge-stale">
              <Clock size={11} /> Approval Expired
            </span>
          ) : (
            <span
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                color: '#f87171',
                border: '1px solid #ef4444',
                borderRadius: '9999px',
                padding: '2px 8px',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <AlertOctagon size={11} /> Awaiting Human Approval
            </span>
          )}
        </div>
      </div>

      {/* Rationale Statement */}
      {proposal.rationale && (
        <div
          style={{
            backgroundColor: '#020617',
            border: '1px solid #1e293b',
            borderRadius: '8px',
            padding: '12px 14px',
            marginBottom: '14px',
          }}
        >
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '4px' }}>
            Autonomous Agent Rationale & Justification
          </div>
          <p style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.4' }}>
            {proposal.rationale}
          </p>
        </div>
      )}

      {/* Parameter Binding Snapshot */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '10px',
          marginBottom: '16px',
        }}
      >
        <div style={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '6px', padding: '8px 12px' }}>
          <div style={{ fontSize: '11px', color: '#64748b' }}>Target Service</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, color: '#38bdf8' }}>
            {String(proposal.parameters.service || 'payment-service')}
          </div>
        </div>

        <div style={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '6px', padding: '8px 12px' }}>
          <div style={{ fontSize: '11px', color: '#64748b' }}>Target Stable Version</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, color: '#4ade80' }}>
            {String(proposal.parameters.target_version || 'v2.8.0')}
          </div>
        </div>

        <div style={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '6px', padding: '8px 12px' }}>
          <div style={{ fontSize: '11px', color: '#64748b' }}>Approved By</div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: proposal.approved_by ? '#f8fafc' : '#64748b' }}>
            {proposal.approved_by || 'Pending Review'}
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {actionError && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: '6px',
            padding: '10px 14px',
            marginBottom: '14px',
            color: '#f87171',
            fontSize: '12px',
          }}
        >
          {actionError}
        </div>
      )}

      {/* Action Decision Controls */}
      {!isExecuted && !isRejected && !isExpired && (
        <div style={{ borderTop: '1px solid #1e293b', paddingTop: '16px' }}>
          {!isApproved ? (
            <div>
              {/* Review Comment Input */}
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                  Operator Review Comment (Optional):
                </label>
                <input
                  type="text"
                  placeholder="e.g. Verified commit diff c4a1b2c leaks asyncpg connection pool"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#020617',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Rejection input dialog */}
              {showRejectInput && (
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '11px', color: '#f87171', marginBottom: '4px' }}>
                    Rejection Explanation (Mandatory for compliance):
                  </label>
                  <input
                    type="text"
                    placeholder="Provide justification for rejecting this remediation..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    style={{
                      width: '100%',
                      backgroundColor: '#020617',
                      border: '1px solid #ef4444',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '12px',
                      outline: 'none',
                    }}
                  />
                </div>
              )}

              {/* Approval / Rejection Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#64748b' }}>
                  <User size={12} color="#38bdf8" />
                  <span>Authorizing as {operatorId} ({operatorRole.toUpperCase()})</span>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  {showRejectInput ? (
                    <>
                      <button
                        onClick={() => setShowRejectInput(false)}
                        style={{
                          backgroundColor: '#1e293b',
                          color: '#94a3b8',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '6px 14px',
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleReject}
                        disabled={isMutating}
                        style={{
                          backgroundColor: '#ef4444',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '6px 14px',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: isMutating ? 'wait' : 'pointer',
                        }}
                      >
                        Confirm Rejection
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setShowRejectInput(true)}
                        disabled={isMutating}
                        style={{
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          color: '#f87171',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          borderRadius: '6px',
                          padding: '6px 14px',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: isMutating ? 'wait' : 'pointer',
                        }}
                      >
                        Reject Proposal
                      </button>
                      <button
                        onClick={handleApprove}
                        disabled={isMutating}
                        style={{
                          backgroundColor: '#38bdf8',
                          color: '#020617',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '6px 18px',
                          fontSize: '12px',
                          fontWeight: 700,
                          cursor: isMutating ? 'wait' : 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <CheckCircle2 size={13} />
                        Approve Proposal
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* Approved: Ready for Execution */
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
                  Proposal Approved & Bound
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                  Safety policy check validated. Ready to trigger controlled service rollback.
                </div>
              </div>

              <button
                onClick={handleExecute}
                disabled={isMutating}
                style={{
                  backgroundColor: '#22c55e',
                  color: '#020617',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 20px',
                  fontSize: '13px',
                  fontWeight: 700,
                  cursor: isMutating ? 'wait' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 0 12px rgba(34, 197, 94, 0.3)',
                }}
              >
                <RotateCcw size={14} />
                Execute Rollback Deployment
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
