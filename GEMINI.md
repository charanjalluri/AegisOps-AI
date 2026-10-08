<!-- GSD:project-start source:PROJECT.md -->

## Project

**AegisOps AI**

AegisOps AI is an evidence-driven AI incident intelligence and autonomous operations platform designed to detect operational problems, investigate them using real-world evidence, determine probable root causes, recommend safe actions, enforce human approval for high-risk operations, execute controlled remediations, and verify resolution. It continuously ingests operational telemetry (logs, metrics, alerts, deployment events) via Apache Kafka, orchestrates investigations via LangGraph and domain-specific Model Context Protocol (MCP) servers, maintains short-term and long-term memory via PostgreSQL and Qdrant, and provides real-time visibility through a React dashboard.

**Core Value:** Detect operational problems automatically, investigate using verifiable evidence across controlled MCP tools, reason with quantified uncertainty, mandate human approval for risky actions, and verify remediation before marking incidents resolved.

### Constraints

- **Security**: Zero plain credentials in LLM prompts or tool arguments; strict read-only boundaries on investigation tools.
- **Local Packaging**: Must spin up fully on a developer workstation via `docker compose up -d` with minimal prerequisites (Docker Desktop, Git, API keys).
- **LLM Compatibility**: Primary reasoning powered by Muse Spark 1.3 Contributor / OpenAI / LangChain compatible interfaces with structured output schemas.
- **Execution Limits**: Strict investigation budget (max 20 tool calls, 5-minute timeout, max 5 expensive operations) to prevent runaway loops.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
