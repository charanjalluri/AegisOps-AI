import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Flame,
  Search,
  Server,
  ShieldAlert,
} from 'lucide-react';
import { IncidentDetail } from '../types/api';

interface IncidentTriageQueueProps {
  incidents: IncidentDetail[];
  selectedIncidentId: string | null;
  onSelectIncident: (incident: IncidentDetail) => void;
  isLoading: boolean;
}

export const IncidentTriageQueue: React.FC<IncidentTriageQueueProps> = ({
  incidents,
  selectedIncidentId,
  onSelectIncident,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'RESOLVED'>('ALL');

  const filteredIncidents = incidents.filter((inc) => {
    // 1. Text filter
    const matchesSearch =
      inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.service.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.incident_id.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    // 2. Tab filter
    if (severityFilter === 'ALL') return true;
    if (severityFilter === 'RESOLVED') return inc.status === 'resolved' || inc.status === 'closed';

    const sevUpper = inc.severity.toUpperCase();
    if (severityFilter === 'CRITICAL') return sevUpper === 'CRITICAL' || sevUpper === 'SEV-1';
    if (severityFilter === 'HIGH') return sevUpper === 'HIGH' || sevUpper === 'SEV-2';
    if (severityFilter === 'MEDIUM') return sevUpper === 'MEDIUM' || sevUpper === 'SEV-3' || sevUpper === 'SEV-4';

    return true;
  });

  const getSeverityBadgeClass = (severity: string, status: string) => {
    if (status === 'resolved' || status === 'closed') return 'badge badge-resolved';
    const s = severity.toUpperCase();
    if (s === 'CRITICAL' || s === 'SEV-1') return 'badge badge-critical';
    if (s === 'HIGH' || s === 'SEV-2') return 'badge badge-high';
    if (s === 'MEDIUM' || s === 'SEV-3') return 'badge badge-medium';
    return 'badge badge-unknown';
  };

  const getSeverityIcon = (severity: string, status: string) => {
    if (status === 'resolved' || status === 'closed') {
      return <CheckCircle size={12} color="#4ade80" />;
    }
    const s = severity.toUpperCase();
    if (s === 'CRITICAL' || s === 'SEV-1') {
      return <Flame size={12} color="#f87171" />;
    }
    if (s === 'HIGH' || s === 'SEV-2') {
      return <AlertTriangle size={12} color="#fbbf24" />;
    }
    return <ShieldAlert size={12} color="#38bdf8" />;
  };

  const formatRelativeTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const diffMs = Date.now() - date.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return 'Just now';
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHours = Math.floor(diffMin / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${Math.floor(diffHours / 24)}d ago`;
    } catch {
      return isoString;
    }
  };

  return (
    <aside
      style={{
        width: '380px',
        backgroundColor: '#090d16',
        borderRight: '1px solid #1e293b',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Search Header */}
      <div style={{ padding: '16px', borderBottom: '1px solid #1e293b' }}>
        <div style={{ position: 'relative', marginBottom: '12px' }}>
          <Search
            size={16}
            color="#64748b"
            style={{ position: 'absolute', left: '12px', top: '10px' }}
          />
          <input
            type="text"
            placeholder="Search service, title, ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#020617',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              padding: '8px 12px 8px 36px',
              color: '#f8fafc',
              fontSize: '13px',
              outline: 'none',
            }}
          />
        </div>

        {/* Severity Filter Tabs */}
        <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '2px' }}>
          {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'RESOLVED'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSeverityFilter(tab)}
              style={{
                backgroundColor: severityFilter === tab ? '#1e293b' : 'transparent',
                color: severityFilter === tab ? '#f8fafc' : '#64748b',
                border: 'none',
                borderRadius: '6px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Incident List Scroll Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {isLoading && incidents.length === 0 ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
            Loading incidents...
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
            No matching incidents found.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {filteredIncidents.map((inc) => {
              const isSelected = inc.incident_id === selectedIncidentId;
              return (
                <div
                  key={inc.incident_id}
                  onClick={() => onSelectIncident(inc)}
                  style={{
                    backgroundColor: isSelected ? '#0f172a' : '#090d16',
                    border: isSelected ? '1px solid #38bdf8' : '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: isSelected ? '0 0 12px rgba(56, 189, 248, 0.15)' : 'none',
                  }}
                >
                  {/* Top Metadata Row */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className={getSeverityBadgeClass(inc.severity, inc.status)}>
                        {getSeverityIcon(inc.severity, inc.status)}
                        {inc.severity}
                      </span>
                      <span
                        style={{
                          fontSize: '11px',
                          color: inc.status === 'resolved' ? '#4ade80' : '#38bdf8',
                          fontWeight: 500,
                          textTransform: 'capitalize',
                        }}
                      >
                        {inc.status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#64748b', fontSize: '11px' }}>
                      <Clock size={11} />
                      <span>{formatRelativeTime(inc.created_at)}</span>
                    </div>
                  </div>

                  {/* Incident Title */}
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: isSelected ? '#f8fafc' : '#e2e8f0',
                      marginBottom: '8px',
                      lineHeight: '1.4',
                    }}
                  >
                    {inc.title}
                  </div>

                  {/* Impacted Service & ID */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        color: '#94a3b8',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      <Server size={11} color="#38bdf8" />
                      <span>{inc.service}</span>
                    </div>

                    <span
                      style={{
                        fontSize: '10px',
                        color: '#64748b',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {inc.incident_id}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};
