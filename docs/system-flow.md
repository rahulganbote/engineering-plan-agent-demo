# System Flow

## End-to-End Walkthrough

This document traces a complete pipeline run from BRD upload to approved engineering bundle, using a realistic example: a product team requesting a real-time notification system.

---

## Step 0 — BRD Upload

The user uploads a BRD via the Streamlit UI. The UI sends it to the FastAPI backend via `POST /run-pipeline`. Accepted formats: `.txt`, `.pdf`, `.docx`.

---

## Step 1 — Security Validation (7 checks, sequential, deterministic)

Before any LLM node runs, the BRD passes through 7 sequential checks:

| Check | What It Does | Failure Behavior |
|---|---|---|
| Format check | Restricts to .txt, .pdf, .docx | Reject with error |
| Size guard | Enforces ≤ 10MB | Reject with error |
| Word count | Requires ≥ 50 words | Reject with error |
| Regex injection scan | Checks 15 known jailbreak/injection strings | Reject with error |
| LLM injection scan | gpt-4o-mini semantic scan for sophisticated injections | Reject with warning |
| PII redaction | Redacts SSN, credit card, email, phone with `[REDACTED-*]` placeholders | Redact and continue |
| Completeness check | Verifies Objectives, Requirements, Constraints, Risks, NFRs present | Warn and continue |

Only after all 7 checks pass (or non-blocking checks complete) does BRD text flow to the Orchestrator.

---

## Step 2 — Orchestrator: BRD Parsing and Routing

The Orchestrator Agent parses the validated BRD into typed sections and builds a routing map for specialist dispatch.

**Example parsed output (simplified):**

```json
{
  "sections": {
    "objectives": "Deliver real-time in-app notifications within 2 seconds...",
    "functional_requirements": ["FR-001: In-app delivery < 2s", "FR-002: Preferences per type", ...],
    "nfrs": ["NFR-001: 50k concurrent users", "NFR-002: p99 < 5s", ...],
    "constraints": ["No WebSocket infrastructure exists", "JWT auth system in place"],
    "risks": ["Scale target unvalidated", "Push provider not selected"]
  },
  "routing": {
    "plan_generator": ["functional_requirements", "nfrs"],
    "schedule_estimator": ["functional_requirements", "constraints"],
    "solution_architect": ["functional_requirements", "nfrs", "constraints"],
    "poc_planner": ["risks", "functional_requirements"],
    "tech_stack": ["constraints", "nfrs"]
  }
}
```

---

## Step 3 — Parallel Specialist Dispatch

All five specialist agents run concurrently via `ThreadPoolExecutor`. Each agent:
1. Receives its assigned BRD sections
2. Queries Pinecone for relevant org-specific context (similarity threshold 0.45)
3. Generates output grounded in retrieved context
4. Returns a typed Pydantic model with mandatory citations

**Wall-clock time:** ~50 seconds (vs >2.5 minutes sequential)

**Example RAG retrieval for Plan Generator:**
```
Query: "notification system milestone planning 50k concurrent users"
Retrieved chunks:
  - engineering_standards/milestone_templates.md [chunk_012]  score: 0.82
  - past_projects/messaging_platform_2023.md [chunk_047]     score: 0.71
  - planning_guidelines/effort_estimation.md [chunk_003]     score: 0.68
```

Each chunk citation is embedded in the agent's output and will be validated by the Critic.

---

## Step 4 — Critic Agent Evaluation

The Critic receives the full `PipelineState` containing all 5 specialist outputs and scores across 4 dimensions.

**Example scoring:**

```json
{
  "groundedness": 3.9,
  "completeness": 4.8,
  "consistency": 4.6,
  "actionability": 4.0,
  "overall_score": 4.33,
  "badge": "green",
  "fm_caps_applied": [],
  "agent_flags": {},
  "decision": "proceed_to_hitl"
}
```

**Example with FM-2 cap applied (no citations from PoC Planner):**

```json
{
  "groundedness": 2.8,
  "overall_score_raw": 4.1,
  "overall_score": 3.9,
  "badge": "amber",
  "fm_caps_applied": ["FM-2: PoC Planner returned zero vector citations"],
  "agent_flags": {"poc_planner": "no_citations"},
  "decision": "targeted_revision"
}
```

---

## Step 5 — Targeted Revision (if triggered)

If the Critic's decision is `targeted_revision` and `revision_count < 2`:

1. Only flagged agents re-run (in this case, PoC Planner)
2. Revision context is injected: Critic findings + specific failure reason
3. Agent output replaces the failed output in `PipelineState`
4. `revision_count` increments
5. Full Critic evaluation runs again on the updated state

After 2 revision cycles, the pipeline always proceeds to HITL regardless of score.

---

## Step 6 — HITL Approval Gate

The user sees the Critic's quality badge, full agent outputs, and the Kroki-rendered architecture diagram.

**UI mode:** Approve / Reject buttons in Streamlit  
**Voice mode:** ElevenLabs conversational agent accepts rating (1–5) + natural language feedback via webhook

**Approval triggers 4 downstream actions:**

1. **Google Sheets** — writes complete run state as a structured audit row; fallback to local CSV if credentials missing
2. **Jira Epic** — MCP client spawns `mcp-atlassian` server over stdio → `jira_create_issue` with ADF body (Critic scores, architectural components, NFR mappings, Kroki diagram link); fallback to REST API if MCP unavailable
3. **Pinecone ingestion** — BRD is embedded and ingested into the vector store for future RAG retrieval
4. **PDF export** — ReportLab generates a structured PDF with all artifacts, available at `GET /download/{run_id}`

**Rejection** writes only an audit row to Google Sheets.

---

## Complete State Machine

```
Upload → Security (7 checks)
    ↓ pass
Orchestrator (parse + route)
    ↓
Parallel dispatch (5 agents, ~50s)
    ↓
Critic evaluation (FM-1/2/3 caps)
    ↓ score < threshold AND revision_count < 2
Targeted revision (failing agents only)
    ↓ re-evaluate
    ↓ score ≥ threshold OR revision_count = 2
HITL Gate
    ↓ approve
Sheets + Jira (MCP) + Pinecone + PDF
    ↓ reject
Audit row only
```

---

## Observability

Every step is traced in LangSmith under the `em-copilot-brd-agent` project. Traces include prompt structure, input/output tokens, latency per agent, and model version. Local JSONL logs are written to `logs/pipeline.jsonl` for air-gapped environments.

A single full run (standard 5-section BRD) costs approximately **$0.31** and completes in approximately **60 seconds** end-to-end including HITL wait time.
