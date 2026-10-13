-- ==============================================================================
-- AegisOps AI - Platform Operational Telemetry & Incident Schema
-- Database: aegisops_db
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Raw Logs Table
CREATE TABLE IF NOT EXISTS raw_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    service VARCHAR(64) NOT NULL,
    level VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    environment VARCHAR(32) DEFAULT 'development',
    trace_id VARCHAR(64),
    metadata JSONB DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_logs_service_timestamp ON raw_logs (service, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_raw_logs_service_level_timestamp ON raw_logs (service, level, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_raw_logs_trace_id ON raw_logs (trace_id) WHERE trace_id IS NOT NULL;

-- 2. Raw Metrics Table
CREATE TABLE IF NOT EXISTS raw_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    service VARCHAR(64) NOT NULL,
    metric_name VARCHAR(128) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(32) DEFAULT 'count',
    dimensions JSONB DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_metrics_service_metric_timestamp ON raw_metrics (service, metric_name, timestamp DESC);

-- 3. Deployment Events Table
CREATE TABLE IF NOT EXISTS deployment_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    service VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    previous_version VARCHAR(32),
    git_commit VARCHAR(64) NOT NULL,
    author VARCHAR(64) DEFAULT 'system',
    status VARCHAR(32) DEFAULT 'completed',
    metadata JSONB DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployment_events_service_timestamp ON deployment_events (service, timestamp DESC);

-- 4. Incidents Table
CREATE TABLE IF NOT EXISTS incidents (
    incident_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    service VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'SEV-2',
    status VARCHAR(32) NOT NULL DEFAULT 'detected',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    summary TEXT NOT NULL,
    primary_root_cause TEXT,
    confidence_score DOUBLE PRECISION,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_incidents_service_status ON incidents (service, status);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents (created_at DESC);

-- 5. Incident Timeline Events Table
CREATE TABLE IF NOT EXISTS incident_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(64) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_incident_events_incident_timestamp ON incident_events (incident_id, timestamp);
