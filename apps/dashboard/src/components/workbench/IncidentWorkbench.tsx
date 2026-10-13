import React, { useEffect, useState } from 'react';
import {
  CheckCircle,
  Clock,
  Compass,
  Cpu,
  Server,
  Shield,
} from 'lucide-react';
import { apiClient } from '../../api/client';
import {
  ActionProposal,
  AuditLogEntry,
  EvidenceItem,
  HypothesisItem,
  IncidentDetail,
  ToolHistoryItem,
  VerificationStatus,
} from '../../types/api';
import { AuditTrailViewer } from '../governance/AuditTrailViewer';
import { HumanApprovalCard } from '../governance/HumanApprovalCard';
import { RemediationVerificationWidget } from '../governance/RemediationVerificationWidget';
import { MCPToolInspector } from '../inspector/MCPToolInspector';
import { EvidenceGallery } from './EvidenceGallery';
import { HypothesisMeter } from './HypothesisMeter';
import { InvestigationTimeline } from './InvestigationTimeline';

interface IncidentWorkbenchProps {
  incident: IncidentDetail;
  onIncidentUpdated?: () => void;
}

export const IncidentWorkbench: React.FC<IncidentWorkbenchProps> = ({
  incident,
  onIncidentUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<'INVESTIGATION' | 'TOOLS' | 'GOVERNANCE'>('INVESTIGATION');
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [hypotheses, setHypotheses] = useState<HypothesisItem[]>([]);
  const [toolHistory, setToolHistory] = useState<ToolHistoryItem[]>([]);
  const [proposals, setProposals] = useState<ActionProposal[]>([]);
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus>({
    status: 'idle',
    samples: [],
    consecutive_passes: 0,
    target_passes: 2,
    conditions: [
      { metric_name: 'error_rate', operator: '<', threshold: 0.01, unit: 'ratio' },
      { metric_name: 'active_connections', operator: '<', threshold: 15.0, unit: 'connections' },
    ],
  });
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);

  const fetchDetails = async () => {
    try {
      const [evData, hypoData, toolData, propData, verifData, auditData] = await Promise.all([
        apiClient.getIncidentEvidence(incident.incident_id),
        apiClient.getIncidentHypotheses(incident.incident_id),
        apiClient.getIncidentTools(incident.incident_id),
        apiClient.getProposals(incident.incident_id),
        apiClient.getVerificationStatus(incident.incident_id),
        apiClient.getAuditLog(),
      ]);
      setEvidence(evData);
      setHypotheses(hypoData);
      setToolHistory(toolData);
      setProposals(propData);
      setVerificationStatus(verifData);
      setAuditLogs(auditData);
    } catch (err) {
      console.error('Failed to load incident investigation details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setIsLoading(true);
    fetchDetails();
  }, [incident.incident_id]);

  const handleApprove = async (proposalId: string, comment?: string) => {
    setIsMutating(true);
    try {
      await apiClient.approveProposal(proposalId, comment);
      await fetchDetails();
      if (onIncidentUpdated) onIncidentUpdated();
    } finally {
      setIsMutating(false);
    }
  };

  const handleReject = async (proposalId: string, reason: string) => {
    setIsMutating(true);
    try {
      await apiClient.rejectProposal(proposalId, reason);
      await fetchDetails();
      if (onIncidentUpdated) onIncidentUpdated();
    } finally {
      setIsMutating(false);
    }
  };

  const handleExecute = async (proposalId: string) => {
    setIsMutating(true);
    try {
      await apiClient.executeProposal(proposalId);
      await fetchDetails();
      if (onIncidentUpdated) onIncidentUpdated();
    } finally {
      setIsMutating(false);
    }
  };

  const handleTriggerVerification = async () => {
    setIsMutating(true);
    try {
      await apiClient.verifyAndCloseIncident(incident.incident_id);
      await fetchDetails();
      if (onIncidentUpdated) onIncidentUpdated();
    } finally {
      setIsMutating(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Incident Header Card */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '20px 24px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span
                style={{
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  fontSize: '11px',
                  fontWeight: 700,
                  backgroundColor:
                    incident.severity === 'CRITICAL' || incident.severity === 'SEV-1'
                      ? 'rgba(239, 68, 68, 0.2)'
                      : 'rgba(245, 158, 11, 0.2)',
                  color:
                    incident.severity === 'CRITICAL' || incident.severity === 'SEV-1'
                      ? '#f87171'
                      : '#fbbf24',
                  border: '1px solid currentColor',
                  textTransform: 'uppercase',
                }}
              >
                {incident.severity}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  color: '#64748b',
                }}
              >
                {incident.incident_id}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  color: incident.status === 'resolved' ? '#4ade80' : '#38bdf8',
                  textTransform: 'uppercase',
                  fontWeight: 600,
                }}
              >
                ● {incident.status}
              </span>
            </div>

            <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
              {incident.title}
            </h1>

            {incident.summary && (
              <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '12px', lineHeight: '1.4' }}>
                {incident.summary}
              </p>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: '#94a3b8', fontSize: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Server size={13} color="#38bdf8" />
                <span style={{ fontFamily: 'var(--font-mono)' }}>Service: {incident.service}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Clock size={13} />
                <span>Detected: {new Date(incident.created_at).toLocaleTimeString()}</span>
              </div>
              {incident.resolved_at && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#4ade80' }}>
                  <CheckCircle size={13} />
                  <span>Resolved: {new Date(incident.resolved_at).toLocaleTimeString()}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            borderTop: '1px solid #1e293b',
            marginTop: '16px',
            paddingTop: '16px',
          }}
        >
          <button
            onClick={() => setActiveTab('INVESTIGATION')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: activeTab === 'INVESTIGATION' ? '#1e293b' : 'transparent',
              color: activeTab === 'INVESTIGATION' ? '#f8fafc' : '#64748b',
              border: '1px solid',
              borderColor: activeTab === 'INVESTIGATION' ? '#38bdf8' : 'transparent',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Compass size={14} color={activeTab === 'INVESTIGATION' ? '#38bdf8' : '#64748b'} />
            <span>Investigation & Evidence</span>
          </button>

          <button
            onClick={() => setActiveTab('TOOLS')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: activeTab === 'TOOLS' ? '#1e293b' : 'transparent',
              color: activeTab === 'TOOLS' ? '#f8fafc' : '#64748b',
              border: '1px solid',
              borderColor: activeTab === 'TOOLS' ? '#38bdf8' : 'transparent',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Cpu size={14} color={activeTab === 'TOOLS' ? '#38bdf8' : '#64748b'} />
            <span>MCP Tool Inspector ({toolHistory.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('GOVERNANCE')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: activeTab === 'GOVERNANCE' ? '#1e293b' : 'transparent',
              color: activeTab === 'GOVERNANCE' ? '#f8fafc' : '#64748b',
              border: '1px solid',
              borderColor: activeTab === 'GOVERNANCE' ? '#38bdf8' : 'transparent',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Shield size={14} color={activeTab === 'GOVERNANCE' ? '#38bdf8' : '#64748b'} />
            <span>Remediation & Governance ({proposals.length})</span>
          </button>
        </div>
      </div>

      {/* Main Tab Content */}
      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
          Loading investigation trace and diagnostic evidence...
        </div>
      ) : activeTab === 'INVESTIGATION' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Calibrated Hypothesis Meter (UI-02) */}
          <HypothesisMeter hypotheses={hypotheses} />

          {/* Canonical Evidence Gallery (UI-02) */}
          <EvidenceGallery evidence={evidence} />

          {/* Investigation Timeline (UI-02) */}
          <InvestigationTimeline evidence={evidence} createdAt={incident.created_at} />
        </div>
      ) : activeTab === 'TOOLS' ? (
        <MCPToolInspector toolHistory={toolHistory} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Human-in-the-Loop Approval Cards (UI-04, GOV-02) */}
          {proposals.length === 0 ? (
            <div
              style={{
                backgroundColor: '#090d16',
                border: '1px dashed #1e293b',
                borderRadius: '10px',
                padding: '32px',
                textAlign: 'center',
                color: '#64748b',
              }}
            >
              No mutating remediation proposals currently formulated for this incident.
            </div>
          ) : (
            proposals.map((prop) => (
              <HumanApprovalCard
                key={prop.id}
                proposal={prop}
                operatorId={apiClient.getOperatorId()}
                operatorRole={apiClient.getOperatorRole()}
                onApprove={handleApprove}
                onReject={handleReject}
                onExecute={handleExecute}
                isMutating={isMutating}
              />
            ))
          )}

          {/* Closed-Loop Telemetry Verification Loop (GOV-03) */}
          <RemediationVerificationWidget
            status={verificationStatus}
            incidentId={incident.incident_id}
            onTriggerVerification={handleTriggerVerification}
            isVerifying={isMutating}
          />

          {/* Immutable Governance Audit Trail Viewer (GOV-04) */}
          <AuditTrailViewer entries={auditLogs} />
        </div>
      )}
    </div>
  );
};
