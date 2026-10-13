import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Code2,
  Database,
  FileSearch,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { EvidenceItem } from '../../types/api';

interface EvidenceGalleryProps {
  evidence: EvidenceItem[];
}

export const EvidenceGallery: React.FC<EvidenceGalleryProps> = ({ evidence }) => {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getSourceIcon = (sourceTool: string) => {
    if (sourceTool.includes('logs')) return <Search size={14} color="#38bdf8" />;
    if (sourceTool.includes('database')) return <Database size={14} color="#a855f7" />;
    if (sourceTool.includes('github')) return <Code2 size={14} color="#f59e0b" />;
    return <FileSearch size={14} color="#22c55e" />;
  };

  const getSourceColor = (sourceTool: string) => {
    if (sourceTool.includes('logs')) return '#38bdf8';
    if (sourceTool.includes('database')) return '#a855f7';
    if (sourceTool.includes('github')) return '#f59e0b';
    return '#22c55e';
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
          <ShieldCheck size={16} color="#38bdf8" />
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Canonical Evidence Chain ({evidence.length} Signals)
          </h3>
        </div>
        <span style={{ fontSize: '12px', color: '#64748b' }}>
          Pre-sanitized verifiable evidence items
        </span>
      </div>

      {evidence.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
          No evidence records captured yet.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '14px' }}>
          {evidence.map((ev) => {
            const isExpanded = !!expandedIds[ev.id];
            const sourceColor = getSourceColor(ev.source_tool);
            const confPercent = Math.round(ev.confidence_weight * 100);

            return (
              <div
                key={ev.id}
                style={{
                  backgroundColor: '#020617',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                {/* Header: Tool Source & Confidence Weight */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {getSourceIcon(ev.source_tool)}
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: sourceColor,
                      }}
                    >
                      {ev.source_tool}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div
                      style={{
                        width: '48px',
                        height: '5px',
                        backgroundColor: '#1e293b',
                        borderRadius: '3px',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${confPercent}%`,
                          height: '100%',
                          backgroundColor: confPercent >= 90 ? '#22c55e' : '#f59e0b',
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: '#f8fafc',
                      }}
                    >
                      {confPercent}%
                    </span>
                  </div>
                </div>

                {/* Signal Classification Badge */}
                <div>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      backgroundColor: 'rgba(56, 189, 248, 0.1)',
                      color: '#38bdf8',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    SIGNAL: {ev.signal_type}
                  </span>
                </div>

                {/* Human Interpretation */}
                <p style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.4' }}>
                  {ev.interpretation}
                </p>

                {/* Raw Payload Collapsible */}
                <div>
                  <button
                    onClick={() => toggleExpand(ev.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'none',
                      border: 'none',
                      color: '#64748b',
                      fontSize: '11px',
                      cursor: 'pointer',
                      padding: '2px 0',
                    }}
                  >
                    {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                    <span>{isExpanded ? 'Hide Raw Structured Data' : 'Inspect Raw Data'}</span>
                  </button>

                  {isExpanded && (
                    <pre
                      style={{
                        marginTop: '8px',
                        padding: '10px',
                        backgroundColor: '#090d16',
                        border: '1px solid #1e293b',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        color: '#94a3b8',
                        overflowX: 'auto',
                        maxHeight: '180px',
                      }}
                    >
                      {JSON.stringify(ev.raw_data, null, 2)}
                    </pre>
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
