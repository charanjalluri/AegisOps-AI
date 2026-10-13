import React, { useState } from 'react';
import {
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  Cpu,
  Terminal,
} from 'lucide-react';
import { ToolHistoryItem } from '../../types/api';

interface MCPToolInspectorProps {
  toolHistory: ToolHistoryItem[];
}

export const MCPToolInspector: React.FC<MCPToolInspectorProps> = ({ toolHistory }) => {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyToClipboard = (id: string, args: Record<string, unknown>) => {
    navigator.clipboard.writeText(JSON.stringify(args, null, 2));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getLatencyBadge = (ms: number) => {
    const color = ms < 100 ? '#4ade80' : ms < 500 ? '#fbbf24' : '#f87171';
    return (
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          fontWeight: 600,
          color,
          backgroundColor: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid #1e293b',
          borderRadius: '4px',
          padding: '2px 8px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
        }}
      >
        <Clock size={11} />
        {ms.toFixed(1)}ms
      </span>
    );
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
          <Cpu size={16} color="#38bdf8" />
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            MCP Tool Call Inspector ({toolHistory.length} Invocations)
          </h3>
        </div>
        <span style={{ fontSize: '12px', color: '#64748b' }}>
          Granular latency & sanitized parameter telemetry
        </span>
      </div>

      {toolHistory.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
          No MCP tool executions recorded yet.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {toolHistory.map((item) => {
            const isExpanded = !!expandedIds[item.id];
            const isCopied = copiedId === item.id;

            return (
              <div
                key={item.id}
                style={{
                  backgroundColor: '#020617',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '14px 16px',
                }}
              >
                {/* Header Row */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      onClick={() => toggleExpand(item.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#94a3b8',
                        cursor: 'pointer',
                        padding: '2px',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                      title={isExpanded ? 'Collapse parameters' : 'Expand parameters'}
                    >
                      {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Terminal size={14} color="#38bdf8" />
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '13px',
                          fontWeight: 600,
                          color: '#f8fafc',
                        }}
                      >
                        {item.tool_name}
                      </span>
                    </div>

                    <span
                      style={{
                        fontSize: '10px',
                        color: '#64748b',
                        backgroundColor: '#0f172a',
                        border: '1px solid #1e293b',
                        borderRadius: '4px',
                        padding: '1px 6px',
                        textTransform: 'uppercase',
                        fontWeight: 600,
                      }}
                    >
                      {item.caller}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {getLatencyBadge(item.duration_ms)}

                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        color: item.status === 'success' ? '#4ade80' : '#f87171',
                        backgroundColor: item.status === 'success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        border: `1px solid ${item.status === 'success' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                        borderRadius: '4px',
                        padding: '2px 8px',
                        textTransform: 'uppercase',
                      }}
                    >
                      {item.status}
                    </span>

                    <span
                      style={{
                        fontSize: '11px',
                        color: '#64748b',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {new Date(item.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {/* Result Summary */}
                {item.result_summary && (
                  <div
                    style={{
                      marginTop: '8px',
                      marginLeft: '26px',
                      fontSize: '12px',
                      color: '#cbd5e1',
                      lineHeight: '1.4',
                    }}
                  >
                    <span style={{ color: '#64748b', fontWeight: 600 }}>Result: </span>
                    {item.result_summary}
                  </div>
                )}

                {/* Expanded Sanitized JSON Arguments */}
                {isExpanded && (
                  <div
                    style={{
                      marginTop: '12px',
                      marginLeft: '26px',
                      backgroundColor: '#090d16',
                      border: '1px solid #1e293b',
                      borderRadius: '6px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 12px',
                        backgroundColor: '#0f172a',
                        borderBottom: '1px solid #1e293b',
                        fontSize: '11px',
                        color: '#94a3b8',
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>Sanitized Input Arguments</span>
                      <button
                        onClick={() => copyToClipboard(item.id, item.arguments)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          background: 'none',
                          border: 'none',
                          color: isCopied ? '#4ade80' : '#38bdf8',
                          fontSize: '11px',
                          cursor: 'pointer',
                        }}
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                        <span>{isCopied ? 'Copied' : 'Copy JSON'}</span>
                      </button>
                    </div>

                    <pre
                      style={{
                        padding: '12px',
                        margin: 0,
                        fontSize: '12px',
                        fontFamily: 'var(--font-mono)',
                        color: '#f8fafc',
                        overflowX: 'auto',
                      }}
                    >
                      {JSON.stringify(item.arguments, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
