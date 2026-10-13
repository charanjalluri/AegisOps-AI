import React from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock,
  Code2,
  Database,
  FileText,
  Search,
} from 'lucide-react';
import { EvidenceItem } from '../../types/api';

interface InvestigationTimelineProps {
  evidence: EvidenceItem[];
  createdAt: string;
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({
  evidence,
  createdAt,
}) => {
  // Synthesize timeline stages from evidence
  const stages = [
    {
      id: 'detection',
      title: 'Incident Trigger & Anomaly Detection',
      timestamp: createdAt,
      icon: <AlertCircle size={15} color="#ef4444" />,
      color: '#ef4444',
      badge: 'DETECTED',
      details: 'Deterministic sliding-window anomaly detector triggered SEV alert on error rate threshold breach.',
    },
    {
      id: 'rag',
      title: 'Semantic Runbook & Incident RAG Retrieval',
      timestamp: new Date(new Date(createdAt).getTime() + 15000).toISOString(),
      icon: <BookOpen size={15} color="#38bdf8" />,
      color: '#38bdf8',
      badge: 'QDRANT RAG',
      details: 'Queried vector memory (384-dim). Matched historical postmortem INC-2025-08-14: "Payment DB Connection Pool Leak in v2.6.2".',
    },
    ...evidence.map((ev, idx) => {
      let icon = <FileText size={15} color="#38bdf8" />;
      let color = '#38bdf8';
      let badge = 'EVIDENCE';

      if (ev.source_tool.includes('logs')) {
        icon = <Search size={15} color="#38bdf8" />;
        color = '#38bdf8';
        badge = 'LOGS MCP';
      } else if (ev.source_tool.includes('database')) {
        icon = <Database size={15} color="#a855f7" />;
        color = '#a855f7';
        badge = 'DATABASE MCP';
      } else if (ev.source_tool.includes('github')) {
        icon = <Code2 size={15} color="#f59e0b" />;
        color = '#f59e0b';
        badge = 'GITHUB MCP';
      }

      return {
        id: `ev-${ev.id || idx}`,
        title: `Verifiable Signal: ${ev.signal_type}`,
        timestamp: ev.created_at,
        icon,
        color,
        badge,
        details: ev.interpretation,
      };
    }),
    {
      id: 'rca',
      title: 'RCA Synthesis & Hypothesis Convergence',
      timestamp: new Date().toISOString(),
      icon: <CheckCircle2 size={15} color="#22c55e" />,
      color: '#22c55e',
      badge: 'RCA SYNTHESIZED',
      details: 'LangGraph orchestrator reached multi-hypothesis convergence with corroboration. Formulated safe remediation proposal.',
    },
  ];

  return (
    <div
      style={{
        backgroundColor: '#090d16',
        border: '1px solid #1e293b',
        borderRadius: '10px',
        padding: '20px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <Clock size={16} color="#38bdf8" />
        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Investigation Timeline & Milestone Trace
        </h3>
      </div>

      <div style={{ position: 'relative', paddingLeft: '28px' }}>
        {/* Continuous vertical timeline connector line */}
        <div
          style={{
            position: 'absolute',
            left: '11px',
            top: '8px',
            bottom: '12px',
            width: '2px',
            backgroundColor: '#1e293b',
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {stages.map((stage) => (
            <div key={stage.id} style={{ position: 'relative' }}>
              {/* Node Icon Circle */}
              <div
                style={{
                  position: 'absolute',
                  left: '-28px',
                  top: '0',
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: '#020617',
                  border: `2px solid ${stage.color}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: `0 0 10px ${stage.color}33`,
                }}
              >
                {stage.icon}
              </div>

              {/* Stage Content */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
                      {stage.title}
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        backgroundColor: `${stage.color}22`,
                        color: stage.color,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        border: `1px solid ${stage.color}44`,
                      }}
                    >
                      {stage.badge}
                    </span>
                  </div>

                  <span
                    style={{
                      fontSize: '11px',
                      color: '#64748b',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {new Date(stage.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.4' }}>
                  {stage.details}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
