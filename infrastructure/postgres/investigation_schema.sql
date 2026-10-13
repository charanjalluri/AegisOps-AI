-- ==============================================================================
-- AegisOps AI - Short-Term Investigation Memory Schema (MEM-01)
-- Database: aegisops_db
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Incident Evidence Table
CREATE TABLE IF NOT EXISTS incident_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    source_tool VARCHAR(64) NOT NULL,
    signal_type VARCHAR(64) NOT NULL,
    confidence_weight DOUBLE PRECISION NOT NULL,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    interpretation TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incident_evidence_incident_created ON incident_evidence (incident_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incident_evidence_source_tool ON incident_evidence (source_tool);

-- 2. Incident Hypotheses Table
CREATE TABLE IF NOT EXISTS incident_hypotheses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    title VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    supporting_evidence JSONB DEFAULT '[]'::jsonb,
    refuting_evidence JSONB DEFAULT '[]'::jsonb,
    rationale TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incident_hypotheses_incident_status ON incident_hypotheses (incident_id, status);

-- 3. Action Proposals Table
CREATE TABLE IF NOT EXISTS action_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    action_type VARCHAR(64) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_level VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'proposed',
    rationale TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_by VARCHAR(64),
    executed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_action_proposals_incident_status ON action_proposals (incident_id, status);

-- 4. Investigation Tool Call History
CREATE TABLE IF NOT EXISTS investigation_tool_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(64) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    tool_name VARCHAR(64) NOT NULL,
    caller VARCHAR(64) NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    duration_ms DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) NOT NULL,
    result_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_investigation_tool_history_incident_created ON investigation_tool_history (incident_id, created_at DESC);
