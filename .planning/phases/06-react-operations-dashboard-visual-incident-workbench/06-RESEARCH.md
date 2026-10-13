# Phase 6: React Operations Dashboard & Visual Incident Workbench - Research & Architecture Contract

## 1. Domain & Purpose

Phase 6 provides the visual operational cockpit for AegisOps AI (`UI-01`, `UI-02`, `UI-03`, `UI-04`, `UI-05`). It bridges the autonomous investigation agents, MCP tool pipelines, and policy engine into a real-time, accessible SRE operations dashboard.

Operators must be able to:
1. Triage active incidents in real time with clear severity and status indicators (`UI-01`).
2. Explore investigation timelines, evidence chains, and calibrated hypothesis rankings grounded in actual Bayesian scoring (`UI-02`).
3. Inspect granular MCP tool executions, execution latency, and sanitized payloads (`UI-03`).
4. Review, approve, or reject mutating action proposals under strict server-side operator authorization, parameter binding, and replay prevention (`UI-04`, `GOV-02`).
5. Monitor platform observability with live active health checks distinguishing healthy, unhealthy, unknown, and stale services (`UI-05`).
6. Observe closed-loop post-remediation verification driven strictly by backend evaluation thresholds (`GOV-03`).

---

## 2. UI/UX Pro Max Design System Decisions

Based on the `ui-ux-pro-max` design intelligence for `"sre incident monitoring operations dashboard"`:

### Palette: OLED Dark Mode (High Information Density, WCAG AAA)
- **Deep Background Canvas:** `#020617` (Slate 950 - eliminates backlight glow, reduces eye strain during active incident triage)
- **Panel / Card Surfaces:** `#0F172A` (Slate 900)
- **Border / Divider Lines:** `#1E293B` (Slate 800)
- **Hover Surfaces:** `#334155` (Slate 700)
- **Primary Text:** `#F8FAFC` (Slate 50 - 15.8:1 contrast against `#020617`)
- **Muted Text / Secondary Labels:** `#94A3B8` (Slate 400 - 7.2:1 contrast against `#020617`)

### Status & Semantic Accent Palette
- **Critical / Outage / Unhealthy:** `#EF4444` (Rose 500) with soft background `#7F1D1D20`
- **Warning / Degraded / Stale / Expired:** `#F59E0B` (Amber 500) with soft background `#78350F20`
- **Recovery / Nominal / Success / Healthy / Verified:** `#22C55E` (Emerald 500) with soft background `#064E3B20`
- **Investigation / Active / Info / Unknown:** `#38BDF8` (Sky 400) / `#64748B` (Slate 500 for Unknown) with soft background `#0C4A6E20`

### Typography Pairing
- **Headings & Body UI:** `Inter`, system sans-serif (clean visual hierarchy, high legibility at 12px–16px)
- **Code, Telemetry, SHAs, Latency, Tool Calls:** `Fira Code` / `JetBrains Mono`, monospace

### Information Architecture & Layout
- **Fixed Header (Top Bar):** Brand mark, live connection status, platform health badge (`UI-05`), current active incident counter, operator ID and role pill.
- **Master-Detail Two-Column Layout (Desktop):**
  - Left Column (380px fixed width): Active Incident Triage Queue (`UI-01`) with search, severity filter tabs (`All`, `Critical`, `High`, `Medium`, `Resolved`), and auto-refresh countdown.
  - Right Area (flex-1 main workbench): Selected Incident Detail (`UI-02`), Investigation Timeline, Evidence Cards, Calibrated Hypothesis Meter, MCP Tool Inspector (`UI-03`), and HITL Approval & Verification Card (`UI-04`, `GOV-03`).

---

## 3. Server-Side Authentication & Operator Authorization Model

Every REST endpoint exposing sensitive operational data or mutating platform state mandates server-side verification:

### Operator Identity & Role Validation
- Privileged endpoints enforce a reusable FastAPI dependency: `Depends(require_operator_authorization)`.
- Requests must supply:
  - `X-Operator-Id`: Non-empty operator identifier (e.g. `sre-lead@aegisops.ai`). If missing or whitespace, returns `HTTP 401 Unauthorized`.
  - `X-Operator-Role`: Authorized operator role (`sre`, `admin`, `oncall`). If missing, defaults to `sre`. Non-privileged roles attempting execution or closure receive `HTTP 403 Forbidden`.
- Privileged endpoints requiring authorization:
  - `POST /api/proposals/{proposal_id}/approve`
  - `POST /api/proposals/{proposal_id}/reject`
  - `POST /api/proposals/{proposal_id}/execute`
  - `POST /api/incidents/{incident_id}/verify-and-close`
  - `GET /api/audit`
- Read-only triage and evidence endpoints (`/api/incidents`, `/api/observability/status`) require valid operator session or header, returning sanitized diagnostic payloads.

---

## 4. Proposal Parameter Binding, Expiration & Replay Prevention

To prevent unauthorized parameter drift, replay attacks, or stale action execution:

1. **Exact Parameter Binding:**
   - An action proposal in `InvestigationStorage` is created with immutable parameters: `{"service": "...", "target_version": "...", "action_type": "rollback_deployment"}`.
   - When an operator approves via `POST /api/proposals/{proposal_id}/approve`, the approval is cryptographically or strictly bound to that exact proposal ID and its stored parameter dictionary.
   - When `POST /api/proposals/{proposal_id}/execute` is called, the endpoint cross-checks incoming parameters (if provided) against the approved proposal parameters. If parameters deviate, execution is aborted with `HTTP 400 Bad Request`.
2. **Approval Expiration (TTL):**
   - Approvals have a configurable expiration window (`approval_ttl_seconds = 1800` / 30 minutes).
   - If an approved proposal is not executed within the TTL window, its state transitions to `expired`.
   - Attempting to execute an expired proposal raises `PolicyViolationError` and returns `HTTP 409 Conflict`.
3. **Single-Use Replay Prevention:**
   - The proposal lifecycle follows a strict monotonic state machine:
     `proposed` $\rightarrow$ `approved` $\rightarrow$ `executed` $\rightarrow$ `verified` (or `rejected` / `expired`).
   - Once executed, the proposal state is permanently updated to `executed` with timestamp and operator record.
   - Subsequent execution attempts on an already `executed` or `verified` proposal are immediately rejected (`HTTP 409 Conflict: Proposal already executed`).

---

## 5. Live Observability Status Architecture (Active Probing)

Rather than assuming or inferring status, `apps/api/routers/observability.py` actively probes infrastructure and services via real TCP/HTTP health checks with strict timeouts:

### 4-State Service Health Model
1. **`healthy`**: Active HTTP probe returns 200 OK or socket connection establishes within timeout, and latest heartbeat is within the last 60 seconds.
2. **`unhealthy`**: Active probe explicitly returns HTTP 5xx, TCP connection refused, or reported error state.
3. **`unknown`**: Probe timed out (timeout > 1.5s), host is unresolvable, or network probe failed without definitive server response.
4. **`stale`**: Service was previously healthy, but no heartbeat or telemetry sample has been received within the configured freshness window (> 60 seconds).

### Probed Targets
- Core Infrastructure: PostgreSQL (`:5432`), Kafka (`:9092`), Qdrant (`:6333`), n8n (`:5678`).
- Managed MCP Servers: Logs (`:8002`), Database (`:8003`), GitHub (`:8004`), Incident (`:8005`), Deployment (`:8006`), n8n (`:8007`).
- Monitored Services: `payment-service` (`:8001/health`).

---

## 6. Grounded Confidence Calibration (Investigation Workbench)

The visual workbench's hypothesis confidence meters (`UI-02`) directly mirror the Bayesian reasoning engine in `apps/agent/reasoning/hypotheses.py`:

1. **Default Competing Hypotheses & Bayesian Priors:**
   - H1: Database Connection Pool Exhaustion (Code Release / Leak) — Prior: `0.40`
   - H2: Database Infrastructure Degradation or Resource Starvation — Prior: `0.25`
   - H3: Organic High Traffic Surge / Transaction Volume Spike — Prior: `0.20`
   - H4: Downstream Gateway / Third-Party Payment Provider Outage — Prior: `0.15`
2. **Single-Source Ceiling (Cap at 70%):**
   - If evidence originates from only $\le 1$ source tool, confidence is strictly capped at `0.70` (70%). The UI displays a `Single-Source Cap (70%)` indicator to prevent overconfidence.
3. **Multi-Source Corroboration Requirement ($\ge 2$ Tools):**
   - A hypothesis cannot exceed `0.85` (85%) confidence without corroborated evidence from $\ge 2$ independent tools (e.g. Logs + Database + GitHub).
   - Once confidence reaches $\ge 0.85$ with $\ge 2$ corroborating tools, the status transitions to `validated`.
4. **Refutation & Normalization:**
   - Hypotheses with contradicted evidence receive likelihood dampening and transition to `refuted` if confidence drops below `0.05`.
   - Confidence distribution across active hypotheses is normalized to sum to 100%.

---

## 7. Backend-Driven Closed-Loop Verification

The frontend UI **never** computes metric thresholds or declares an incident recovered on its own:

1. **Backend Evaluation Authority:**
   - Metric collection, sampling windows, and threshold evaluation (`error_rate < 0.01`, `active_connections < 15.0`, `min_consecutive_successes = 2`) are exclusively executed by `RemediationVerifier` (`apps/verification/verifier.py`) and `IncidentClosurePipeline` (`apps/verification/closure.py`).
2. **Verification UI Contract:**
   - The frontend polls `GET /api/incidents/{incident_id}/verification-status` or invokes `POST /api/incidents/{incident_id}/verify-and-close`.
   - The UI displays backend-provided `MetricSample` telemetry streams, threshold progress counters, and the authoritative backend status (`in_progress`, `verified`, `failed`, `escalated`).
   - Incident closure is rendered only when the backend returns `ClosureResult(status="resolved")` with an immutable audit ID.

---

## 8. Frontend Technology Stack & Build Architecture

- **Project Location:** `apps/dashboard/`
- **Build Tool:** Vite 5.x with `@vitejs/plugin-react`
- **Language:** TypeScript 5.x
- **Icons:** `lucide-react` (clean, accessible SVG icons; zero emoji icons)
- **Styling:** Vanilla CSS design tokens with scoped CSS classes adhering to UI/UX Pro Max OLED palette
- **HTTP Client:** Native `fetch` with typed API client wrapper, auto-attaching operator auth headers (`X-Operator-Id`, `X-Operator-Role`)
- **Dev Server Proxy:** Vite config proxies `/api` and `/health` requests to `http://localhost:8000`

---

## 9. Security & Safety Boundaries

1. **Zero Frontend Remediation Bypass:** The frontend contains NO direct connections to deployment infrastructure, Docker, or mutating MCP servers. All actions route strictly through backend policy-gated endpoints.
2. **Server-Side Policy Gate:** `POST /api/proposals/{proposal_id}/execute` delegates directly to `DeploymentTools.rollback_deployment()`, which calls `PolicyEngine.validate_execution_allowed()`. Unapproved, expired, or mismatched executions raise `PolicyViolationError (-32003)`.
3. **Pre-Sanitized MCP Payloads:** The MCP Tool Inspector only renders arguments and results pre-sanitized by backend `Sanitizer`. Passwords, authorization tokens, and credentials are never transmitted to the browser.
4. **Immutable Audit Trail:** All approval, rejection, execution, and verification events write durable entries to `GovernanceAuditLogger`.
5. **Dual Testing Strategy:** Fast offline unit tests (`pytest tests/unit/test_api_*.py`, <5s) test isolation and mocks; live integration tests (`pytest tests/integration/test_dashboard_api_live.py`, `@pytest.mark.integration`) verify running API routers and service interactions.
