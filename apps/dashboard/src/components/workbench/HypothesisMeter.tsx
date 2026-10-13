import React from 'react';
import {
  AlertCircle,
  Award,
  CheckCircle2,
  Compass,
  Layers,
  Scale,
  XCircle,
} from 'lucide-react';
import { HypothesisItem } from '../../types/api';

interface HypothesisMeterProps {
  hypotheses: HypothesisItem[];
}

export const HypothesisMeter: React.FC<HypothesisMeterProps> = ({ hypotheses }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'validated':
        return (
          <span className="badge badge-healthy">
            <CheckCircle2 size={11} /> Validated
          </span>
        );
      case 'refuted':
        return (
          <span className="badge badge-critical">
            <XCircle size={11} /> Refuted
          </span>
        );
      default:
        return (
          <span className="badge badge-medium">
            <Compass size={11} /> Active
          </span>
        );
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#090d16',
        border: '1px solid #1e293b',
        borderRadius: '10px',
        padding: '20px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Scale size={16} color="#38bdf8" />
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Bayesian Hypothesis Confidence Calibration
          </h3>
        </div>
        <span style={{ fontSize: '12px', color: '#64748b' }}>
          Normalized Bayesian posterior distribution
        </span>
      </div>

      {hypotheses.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
          No diagnostic hypotheses evaluated yet.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {hypotheses.map((hypo, idx) => {
            const isWinner = idx === 0 && hypo.status === 'validated';
            const toolsCount = hypo.source_tools_used?.length || 0;
            const isSingleSourceCapped = toolsCount <= 1 && hypo.confidence_score >= 0.65;
            const isCorroborated = toolsCount >= 2;
            const scorePercent = Math.round(hypo.confidence_score * 100);
            const priorPercent = hypo.prior_probability ? Math.round(hypo.prior_probability * 100) : null;

            return (
              <div
                key={hypo.id}
                style={{
                  backgroundColor: '#020617',
                  border: isWinner ? '1px solid #22c55e' : '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '16px',
                  boxShadow: isWinner ? '0 0 12px rgba(34, 197, 94, 0.15)' : 'none',
                }}
              >
                {/* Header Row: Rank, Title, Status */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                    {isWinner && (
                      <span
                        style={{
                          backgroundColor: 'rgba(34, 197, 94, 0.2)',
                          color: '#4ade80',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <Award size={13} /> WINNING ROOT CAUSE
                      </span>
                    )}
                    <span style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc' }}>
                      {hypo.title}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {getStatusBadge(hypo.status)}
                  </div>
                </div>

                {/* Calibration Bar */}
                <div style={{ margin: '12px 0 8px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#94a3b8' }}>
                      {priorPercent !== null && (
                        <span>Prior: {priorPercent}%</span>
                      )}
                      <span>→</span>
                      <span style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                        Posterior: {scorePercent}%
                      </span>
                    </div>

                    {/* Calibration Guardrail Badges */}
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {isSingleSourceCapped && (
                        <span
                          style={{
                            fontSize: '10px',
                            color: '#fbbf24',
                            backgroundColor: 'rgba(245, 158, 11, 0.15)',
                            padding: '1px 6px',
                            borderRadius: '4px',
                            border: '1px solid rgba(245, 158, 11, 0.3)',
                          }}
                        >
                          Single-Source Cap (Max 70%)
                        </span>
                      )}
                      {isCorroborated && (
                        <span
                          style={{
                            fontSize: '10px',
                            color: '#4ade80',
                            backgroundColor: 'rgba(34, 197, 94, 0.15)',
                            padding: '1px 6px',
                            borderRadius: '4px',
                            border: '1px solid rgba(34, 197, 94, 0.3)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '3px',
                          }}
                        >
                          <CheckCircle2 size={10} /> Corroborated ({toolsCount} tools)
                        </span>
                      )}
                    </div>
                  </div>

                  <div
                    style={{
                      height: '8px',
                      backgroundColor: '#1e293b',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${scorePercent}%`,
                        height: '100%',
                        backgroundColor:
                          hypo.status === 'validated'
                            ? '#22c55e'
                            : hypo.status === 'refuted'
                            ? '#ef4444'
                            : '#38bdf8',
                        transition: 'width 0.5s ease',
                      }}
                    />
                  </div>
                </div>

                {/* Rationale & Source Tools */}
                {hypo.rationale && (
                  <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.4', marginTop: '8px' }}>
                    {hypo.rationale}
                  </p>
                )}

                {/* Evidence Links Footprint */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '10px', fontSize: '11px', color: '#64748b' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Layers size={12} color="#38bdf8" />
                    <span>Supporting Signals: {hypo.supporting_evidence?.length || 0}</span>
                  </div>
                  {hypo.refuting_evidence && hypo.refuting_evidence.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#f87171' }}>
                      <AlertCircle size={12} />
                      <span>Refuting Signals: {hypo.refuting_evidence.length}</span>
                    </div>
                  )}
                  {hypo.source_tools_used && hypo.source_tools_used.length > 0 && (
                    <div style={{ fontFamily: 'var(--font-mono)', color: '#94a3b8' }}>
                      Tools: {hypo.source_tools_used.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
