/**
 * AegisOps AI — Platform API TypeScript Definitions
 */

export type ServiceHealthStatus = 'healthy' | 'unhealthy' | 'unknown' | 'stale';

export interface ServiceHealthItem {
  service: string;
  port: number;
  status: ServiceHealthStatus;
  latency_ms: number;
  last_probe_timestamp: string;
  details?: string;
}

export interface ObservabilityStatus {
  overall_status: 'healthy' | 'degraded' | 'outage';
  healthy_count: number;
  total_count: number;
  probed_at: string;
  services: ServiceHealthItem[];
}

export interface IncidentDetail {
  incident_id: string;
  title: string;
  service: string;
  severity: string;
  status: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface EvidenceItem {
  id: string;
  incident_id: string;
  source_tool: string;
  signal_type: string;
  confidence_weight: number;
  raw_data: Record<string, unknown>;
  interpretation: string;
  created_at: string;
}

export interface HypothesisItem {
  id: string;
  incident_id: string;
  title: string;
  status: 'active' | 'validated' | 'refuted' | 'inconclusive';
  confidence_score: number;
  prior_probability?: number;
  supporting_evidence: string[];
  refuting_evidence: string[];
  source_tools_used?: string[];
  rationale?: string;
  updated_at: string;
}

export interface ToolHistoryItem {
  id: string;
  incident_id: string;
  tool_name: string;
  caller: string;
  arguments: Record<string, unknown>;
  duration_ms: number;
  status: string;
  result_summary?: string;
  created_at: string;
}

export interface ActionProposal {
  id: string;
  incident_id: string;
  action_type: string;
  parameters: Record<string, unknown>;
  risk_level: string;
  status: 'proposed' | 'approved' | 'rejected' | 'executed' | 'verified' | 'expired';
  rationale?: string;
  created_at: string;
  approved_by?: string;
  executed_at?: string;
}

export interface MetricSample {
  timestamp: string;
  metric_name: string;
  value: number;
  passed: boolean;
}

export interface MetricCondition {
  metric_name: string;
  operator: string;
  threshold: number;
  unit: string;
}

export interface VerificationStatus {
  status: 'idle' | 'in_progress' | 'verified' | 'failed' | 'escalated';
  samples: MetricSample[];
  consecutive_passes: number;
  target_passes: number;
  conditions: MetricCondition[];
  summary?: string;
}

export interface AuditLogEntry {
  audit_id: string;
  timestamp: string;
  event_type: string;
  action_type?: string;
  risk_level?: string;
  decision?: string;
  operator_id?: string;
  proposal_id?: string;
  incident_id?: string;
  target_service?: string;
  details?: Record<string, unknown>;
}
