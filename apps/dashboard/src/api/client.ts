/**
 * AegisOps AI — Platform Typed API Client
 * Automatically attaches operator authorization headers (X-Operator-Id, X-Operator-Role).
 */

import {
  ActionProposal,
  AuditLogEntry,
  EvidenceItem,
  HypothesisItem,
  IncidentDetail,
  ObservabilityStatus,
  ToolHistoryItem,
  VerificationStatus,
} from '../types/api';

class ApiClient {
  private operatorId: string = 'sre-lead@aegisops.ai';
  private operatorRole: string = 'sre';

  public setOperator(operatorId: string, role: string = 'sre') {
    this.operatorId = operatorId;
    this.operatorRole = role;
  }

  public getOperatorId(): string {
    return this.operatorId;
  }

  public getOperatorRole(): string {
    return this.operatorRole;
  }

  private getHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'X-Operator-Id': this.operatorId,
      'X-Operator-Role': this.operatorRole,
    };
  }

  private async fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errorMsg = `Request failed with status ${res.status}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fall back to status code
      }
      throw new Error(errorMsg);
    }

    return res.json();
  }

  // Incidents API
  public async getIncidents(status?: string, severity?: string, limit: number = 50): Promise<IncidentDetail[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    if (limit) params.append('limit', limit.toString());

    const query = params.toString() ? `?${params.toString()}` : '';
    try {
      return await this.fetchJson<IncidentDetail[]>(`/api/incidents${query}`);
    } catch (err) {
      console.warn('API fetch incidents failed, using fallback:', err);
      return this.getMockIncidents();
    }
  }

  public async getIncident(incidentId: string): Promise<IncidentDetail> {
    try {
      return await this.fetchJson<IncidentDetail>(`/api/incidents/${incidentId}`);
    } catch {
      const mock = this.getMockIncidents().find((i) => i.incident_id === incidentId);
      if (mock) return mock;
      throw new Error(`Incident ${incidentId} not found`);
    }
  }

  public async getIncidentEvidence(incidentId: string): Promise<EvidenceItem[]> {
    try {
      return await this.fetchJson<EvidenceItem[]>(`/api/incidents/${incidentId}/evidence`);
    } catch {
      return this.getMockEvidence(incidentId);
    }
  }

  public async getIncidentHypotheses(incidentId: string): Promise<HypothesisItem[]> {
    try {
      return await this.fetchJson<HypothesisItem[]>(`/api/incidents/${incidentId}/hypotheses`);
    } catch {
      return this.getMockHypotheses(incidentId);
    }
  }

  public async getIncidentTools(incidentId: string): Promise<ToolHistoryItem[]> {
    try {
      return await this.fetchJson<ToolHistoryItem[]>(`/api/incidents/${incidentId}/tools`);
    } catch {
      return this.getMockToolHistory(incidentId);
    }
  }

  // Observability API
  public async getObservabilityStatus(): Promise<ObservabilityStatus> {
    try {
      return await this.fetchJson<ObservabilityStatus>('/api/observability/status');
    } catch (err) {
      console.warn('API fetch observability failed, using fallback:', err);
      return this.getMockObservability();
    }
  }

  // Governance API
  public async getProposals(incidentId: string): Promise<ActionProposal[]> {
    try {
      return await this.fetchJson<ActionProposal[]>(`/api/incidents/${incidentId}/proposals`);
    } catch {
      return this.getMockProposals(incidentId);
    }
  }

  public async approveProposal(proposalId: string, comment?: string): Promise<ActionProposal> {
    return this.fetchJson<ActionProposal>(`/api/proposals/${proposalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    });
  }

  public async rejectProposal(proposalId: string, reason: string): Promise<ActionProposal> {
    return this.fetchJson<ActionProposal>(`/api/proposals/${proposalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  public async executeProposal(proposalId: string, parameters?: Record<string, unknown>): Promise<unknown> {
    return this.fetchJson<unknown>(`/api/proposals/${proposalId}/execute`, {
      method: 'POST',
      body: JSON.stringify(parameters || {}),
    });
  }

  public async getVerificationStatus(incidentId: string): Promise<VerificationStatus> {
    try {
      return await this.fetchJson<VerificationStatus>(`/api/incidents/${incidentId}/verification-status`);
    } catch {
      return {
        status: 'idle',
        samples: [],
        consecutive_passes: 0,
        target_passes: 2,
        conditions: [
          { metric_name: 'error_rate', operator: '<', threshold: 0.01, unit: 'ratio' },
          { metric_name: 'active_connections', operator: '<', threshold: 15.0, unit: 'connections' },
        ],
      };
    }
  }

  public async verifyAndCloseIncident(incidentId: string): Promise<unknown> {
    return this.fetchJson<unknown>(`/api/incidents/${incidentId}/verify-and-close`, {
      method: 'POST',
    });
  }

  public async getAuditLog(): Promise<AuditLogEntry[]> {
    try {
      return await this.fetchJson<AuditLogEntry[]>('/api/audit');
    } catch {
      return [];
    }
  }

  // --- Fallback Seed Data for Offline / Scaffolding Resiliency ---
  private getMockIncidents(): IncidentDetail[] {
    return [
      {
        incident_id: 'inc-payment-leak-01',
        title: 'Payment Service Database Connection Pool Exhaustion',
        service: 'payment-service',
        severity: 'CRITICAL',
        status: 'investigating',
        summary: 'Elevated 500 error rates and connection timeouts following release v2.8.1.',
        created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
        resolved_at: null,
      },
      {
        incident_id: 'inc-order-gateway-02',
        title: 'Order Processing Ingestion Latency Degraded',
        service: 'order-service',
        severity: 'HIGH',
        status: 'detected',
        summary: 'Kafka consumer group lag exceeded 15,000 messages on topic payment.events.',
        created_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
        resolved_at: null,
      },
      {
        incident_id: 'inc-inventory-sync-03',
        title: 'Catalog Cache Synchronization Stale',
        service: 'inventory-service',
        severity: 'MEDIUM',
        status: 'resolved',
        summary: 'Redis cache TTL expiration cycle re-established nominal throughput.',
        created_at: new Date(Date.now() - 120 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        resolved_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      },
    ];
  }

  private getMockObservability(): ObservabilityStatus {
    return {
      overall_status: 'degraded',
      healthy_count: 9,
      total_count: 11,
      probed_at: new Date().toISOString(),
      services: [
        { service: 'postgresql', port: 5432, status: 'healthy', latency_ms: 1.2, last_probe_timestamp: new Date().toISOString(), details: 'TCP socket responsive.' },
        { service: 'kafka', port: 29092, status: 'healthy', latency_ms: 2.1, last_probe_timestamp: new Date().toISOString(), details: 'KRaft broker active.' },
        { service: 'qdrant', port: 6333, status: 'healthy', latency_ms: 3.4, last_probe_timestamp: new Date().toISOString(), details: 'Vector collections accessible.' },
        { service: 'n8n', port: 5678, status: 'healthy', latency_ms: 5.8, last_probe_timestamp: new Date().toISOString(), details: 'Webhook dispatcher active.' },
        { service: 'payment-service', port: 8001, status: 'unhealthy', latency_ms: 245.0, last_probe_timestamp: new Date().toISOString(), details: 'HTTP 500: Database connection pool exhausted.' },
        { service: 'mcp_logs', port: 8002, status: 'healthy', latency_ms: 4.1, last_probe_timestamp: new Date().toISOString(), details: 'Log queries responsive.' },
        { service: 'mcp_database', port: 8003, status: 'healthy', latency_ms: 2.8, last_probe_timestamp: new Date().toISOString(), details: 'Metrics queries responsive.' },
        { service: 'mcp_github', port: 8004, status: 'healthy', latency_ms: 8.2, last_probe_timestamp: new Date().toISOString(), details: 'Local git provider active.' },
        { service: 'mcp_incident', port: 8005, status: 'healthy', latency_ms: 1.9, last_probe_timestamp: new Date().toISOString(), details: 'Investigation storage connected.' },
        { service: 'mcp_deployment', port: 8006, status: 'healthy', latency_ms: 3.1, last_probe_timestamp: new Date().toISOString(), details: 'Deployment manager ready.' },
        { service: 'mcp_n8n', port: 8007, status: 'stale', latency_ms: 0.0, last_probe_timestamp: new Date().toISOString(), details: 'Last heartbeat received 75s ago.' },
      ],
    };
  }

  private getMockEvidence(incidentId: string): EvidenceItem[] {
    return [
      {
        id: 'ev-1',
        incident_id: incidentId,
        source_tool: 'mcp_logs:get_error_rate',
        signal_type: 'error_rate_anomaly',
        confidence_weight: 0.95,
        raw_data: { error_rate: 0.045, threshold: 0.01 },
        interpretation: 'Error rate spiked to 4.5% immediately following deployment v2.8.1.',
        created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
      },
      {
        id: 'ev-2',
        incident_id: incidentId,
        source_tool: 'mcp_database:get_connection_pool_status',
        signal_type: 'pool_exhaustion',
        confidence_weight: 0.98,
        raw_data: { active_connections: 100, max_connections: 100, waiting_queries: 42 },
        interpretation: 'Connection pool exhausted (100/100 active connections). 42 queries queued.',
        created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      },
      {
        id: 'ev-3',
        incident_id: incidentId,
        source_tool: 'mcp_github:get_commit_diff',
        signal_type: 'code_diff_leak',
        confidence_weight: 0.92,
        raw_data: { commit_sha: 'c4a1b2c', file: 'payment_handler.go', lines_added: '+ db.AcquireConnectionWithoutClose()' },
        interpretation: 'Commit c4a1b2c introduced connection acquisition in hot path missing defer db.Close().',
        created_at: new Date(Date.now() - 7 * 60 * 1000).toISOString(),
      },
    ];
  }

  private getMockHypotheses(incidentId: string): HypothesisItem[] {
    return [
      {
        id: 'hypo-1',
        incident_id: incidentId,
        title: 'H1: Database Connection Pool Exhaustion (Code Release / Leak)',
        status: 'validated',
        confidence_score: 0.92,
        prior_probability: 0.4,
        supporting_evidence: ['ev-1', 'ev-2', 'ev-3'],
        refuting_evidence: [],
        source_tools_used: ['mcp_logs', 'mcp_database', 'mcp_github'],
        rationale: 'Corroborated across 3 independent tools: logs show error spike, DB tools confirm pool exhaustion, and git diff reveals unclosed connection.',
        updated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      },
      {
        id: 'hypo-2',
        incident_id: incidentId,
        title: 'H2: Database Infrastructure Degradation or Resource Starvation',
        status: 'refuted',
        confidence_score: 0.04,
        prior_probability: 0.25,
        supporting_evidence: [],
        refuting_evidence: ['ev-2'],
        source_tools_used: ['mcp_database'],
        rationale: 'CPU and disk I/O metrics are nominal (12% CPU); contention is purely software connection leak.',
        updated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      },
      {
        id: 'hypo-3',
        incident_id: incidentId,
        title: 'H3: Organic High Traffic Surge / Transaction Volume Spike',
        status: 'refuted',
        confidence_score: 0.03,
        prior_probability: 0.2,
        supporting_evidence: [],
        refuting_evidence: ['ev-1'],
        source_tools_used: ['mcp_logs'],
        rationale: 'Traffic throughput is within normal 100 req/sec envelope; error rate is isolated to connection pool.',
        updated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      },
      {
        id: 'hypo-4',
        incident_id: incidentId,
        title: 'H4: Downstream Gateway / Third-Party Payment Provider Outage',
        status: 'refuted',
        confidence_score: 0.01,
        prior_probability: 0.15,
        supporting_evidence: [],
        refuting_evidence: ['ev-1'],
        source_tools_used: ['mcp_logs'],
        rationale: 'External payment gateway response time is nominal (< 85ms).',
        updated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      },
    ];
  }

  private getMockToolHistory(incidentId: string): ToolHistoryItem[] {
    return [
      {
        id: 'tool-1',
        incident_id: incidentId,
        tool_name: 'mcp_logs:get_error_rate',
        caller: 'agent',
        arguments: { service: 'payment-service', window_minutes: 5 },
        duration_ms: 84.5,
        status: 'success',
        result_summary: 'Error rate 4.5% (threshold 1.0%)',
        created_at: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
      },
      {
        id: 'tool-2',
        incident_id: incidentId,
        tool_name: 'mcp_database:get_connection_pool_status',
        caller: 'agent',
        arguments: { service: 'payment-service' },
        duration_ms: 42.1,
        status: 'success',
        result_summary: 'active_connections=100/100, waiting=42',
        created_at: new Date(Date.now() - 11 * 60 * 1000).toISOString(),
      },
      {
        id: 'tool-3',
        incident_id: incidentId,
        tool_name: 'mcp_github:get_commit_diff',
        caller: 'agent',
        arguments: { service: 'payment-service', commit_sha: 'c4a1b2c' },
        duration_ms: 125.6,
        status: 'success',
        result_summary: 'Found connection leak in payment_handler.go',
        created_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
      },
    ];
  }

  private getMockProposals(incidentId: string): ActionProposal[] {
    return [
      {
        id: 'prop-rollback-1',
        incident_id: incidentId,
        action_type: 'rollback_deployment',
        parameters: { service: 'payment-service', target_version: 'v2.8.0', previous_version: 'v2.8.1' },
        risk_level: 'HIGH',
        status: 'proposed',
        rationale: 'Rollback payment-service to stable release v2.8.0 to eliminate unclosed connection leak introduced in v2.8.1 commit c4a1b2c.',
        created_at: new Date(Date.now() - 6 * 60 * 1000).toISOString(),
      },
    ];
  }
}

export const apiClient = new ApiClient();
