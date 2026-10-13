import React, { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import { Header } from './components/Header';
import { IncidentTriageQueue } from './components/IncidentTriageQueue';
import { ObservabilityDrawer } from './components/ObservabilityDrawer';
import { IncidentWorkbench } from './components/workbench/IncidentWorkbench';
import { IncidentDetail, ObservabilityStatus } from './types/api';

export const App: React.FC = () => {
  const [incidents, setIncidents] = useState<IncidentDetail[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<IncidentDetail | null>(null);
  const [observability, setObservability] = useState<ObservabilityStatus | null>(null);
  const [isObservabilityOpen, setIsObservabilityOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = async (refresh: boolean = false) => {
    if (refresh) setIsRefreshing(true);
    try {
      const [incList, obs] = await Promise.all([
        apiClient.getIncidents(),
        apiClient.getObservabilityStatus(),
      ]);
      setIncidents(incList);
      setObservability(obs);

      // Auto-select first incident if none selected
      if (incList.length > 0 && !selectedIncident) {
        setSelectedIncident(incList[0]);
      }
    } catch (err) {
      console.error('Failed to load platform data:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    // Periodic auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadData(false);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const activeIncidents = incidents.filter(
    (i) => i.status !== 'resolved' && i.status !== 'closed'
  );

  return (
    <div className="app-container">
      <Header
        observability={observability}
        activeIncidentCount={activeIncidents.length}
        onOpenObservability={() => setIsObservabilityOpen(true)}
        onRefresh={() => loadData(true)}
        isRefreshing={isRefreshing}
        operatorId={apiClient.getOperatorId()}
        operatorRole={apiClient.getOperatorRole()}
      />

      <main className="main-workbench-layout">
        {/* Left Column: Triage Queue (UI-01) */}
        <IncidentTriageQueue
          incidents={incidents}
          selectedIncidentId={selectedIncident?.incident_id || null}
          onSelectIncident={(inc) => setSelectedIncident(inc)}
          isLoading={isLoading}
        />

        {/* Right Area: Selected Incident Workbench (UI-02, UI-03) */}
        <section
          style={{
            flex: 1,
            backgroundColor: '#020617',
            overflowY: 'auto',
            padding: '24px',
          }}
        >
          {selectedIncident ? (
            <IncidentWorkbench incident={selectedIncident} />
          ) : (
            <div style={{ padding: '64px 0', textAlign: 'center', color: '#64748b' }}>
              Select an incident from the triage queue to open the investigation workbench.
            </div>
          )}
        </section>
      </main>

      {/* Slide-over Observability Drawer (UI-05) */}
      <ObservabilityDrawer
        isOpen={isObservabilityOpen}
        onClose={() => setIsObservabilityOpen(false)}
        observability={observability}
        onRefresh={() => loadData(true)}
        isRefreshing={isRefreshing}
      />
    </div>
  );
};

export default App;
