import React, { useState } from 'react';
import {
  FileCheck,
  User,
} from 'lucide-react';
import { AuditLogEntry } from '../../types/api';

interface AuditTrailViewerProps {
  entries: AuditLogEntry[];
}

export const AuditTrailViewer: React.FC<AuditTrailViewerProps> = ({ entries }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredEntries = entries.filter((e) => {
    return (
      e.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (e.operator_id && e.operator_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (e.action_type && e.action_type.toLowerCase().includes(searchTerm.toLowerCase())) ||
      e.audit_id.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

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
          <FileCheck size={16} color="#38bdf8" />
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Immutable Governance Audit Trail ({entries.length} Records)
          </h3>
        </div>

        <div style={{ width: '240px' }}>
          <input
            type="text"
            placeholder="Search audit trail..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#020617',
              border: '1px solid #1e293b',
              borderRadius: '6px',
              padding: '6px 12px',
              color: '#f8fafc',
              fontSize: '12px',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {filteredEntries.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
          No audit records found matching criteria.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filteredEntries.map((item) => (
            <div
              key={item.audit_id}
              style={{
                backgroundColor: '#020617',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px',
                      fontWeight: 700,
                      backgroundColor: 'rgba(56, 189, 248, 0.15)',
                      color: '#38bdf8',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                    }}
                  >
                    {item.event_type}
                  </span>

                  {item.action_type && (
                    <span style={{ fontSize: '12px', color: '#e2e8f0', fontWeight: 600 }}>
                      {item.action_type}
                    </span>
                  )}
                </div>

                <span style={{ fontSize: '11px', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                  {new Date(item.timestamp).toLocaleString()}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={12} color="#38bdf8" />
                  <span>Operator: {item.operator_id || 'system'}</span>
                  {item.decision && <span>• Decision: {item.decision}</span>}
                </div>

                <span style={{ fontFamily: 'var(--font-mono)', color: '#475569' }}>
                  ID: {item.audit_id.substring(0, 13)}...
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
