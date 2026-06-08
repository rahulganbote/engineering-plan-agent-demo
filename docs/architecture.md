# System Architecture

## Overview

EM Copilot is a 7-agent LangGraph system that transforms a raw BRD into an audit-ready engineering bundle. The architecture is built around three core design decisions: parallel specialist dispatch, a self-correcting Critic loop, and a deterministic security layer that runs before any LLM node touches the document.

---

## Design Principles

**Parallel dispatch over sequential chaining.** Five specialist agents run concurrently via `ThreadPoolExecutor`. This reduces wall-clock execution time by ~3× (~50 seconds vs >2.5 minutes sequential). Parallelism is safe because the specialists operate on separate BRD sections with no inter-agent dependencies at dispatch time.

**Pydantic-enforced output contracts.** Every agent returns a typed Pydantic model. There are zero untyped LLM handoffs. Schema validation happens at every boundary, if an agent returns malformed output, the pipeline catches it at the boundary rather than propagating bad data downstream.

**Deterministic failure-mode caps.** The Critic Agent uses an LLM judge, which can be overly optimistic. Three deterministic rules override the Critic's scoring to prevent silent quality degradation (see FM-1/2/3 below).

**Targeted revision, not full replay.** When the Critic flags quality issues, only the failing agents re-run (max 2 cycles). The full pipeline does not restart. This keeps revision cost proportional to the problem.

**Security before intelligence.** A 7-check deterministic security pipeline runs before any LLM node. No BRD text reaches a language model until it has passed format validation, injection scanning, PII redaction, and completeness checking.

---

## Agent Inventory

| Agent | Model | Role | Pattern |
|---|---|---|---|
| Orchestrator | gpt-4o-mini | Parses BRD, extracts sections, routes to specialists | Hub dispatcher |
| Plan Generator | gpt-4o | Creates phased engineering plan with milestones and owners | RAG + Reflection |
| Schedule Estimator | gpt-4o | Maps milestones to sprint timeline with effort estimates | RAG + Timeline |
| Solution Architect | gpt-4o | Generates Mermaid diagram, rendered to SVG via Kroki | RAG + Diagram |
| PoC Planner | gpt-4o | Defines PoC scope, success criteria, and risk reduction | RAG + Scoping |
| Tech Stack Recommender | gpt-4o | Evaluates technology options against org standards | RAG + Org context |
| Critic Agent | gpt-4o-mini | Quality audit, revision routing, FM cap enforcement | LLM-as-Judge |

---

## Full Data Flow

```
BRD Upload (Streamlit UI)
      │
      ▼ POST /run-pipeline (FastAPI)
┌──────────────────────────────────────────────────────┐
│              SECURITY VALIDATION LAYER               │
│                                                      │
│  1. Format check  (.txt / .pdf / .docx only)         │
│  2. Size guard    (≤ 10MB)                           │
│  3. Word count    (≥ 50 words)                       │
│  4. Regex scan    (15 known injection patterns)      │
│  5. LLM scan      (gpt-4o-mini semantic injection)   │
│  6. PII redact    (SSN, CC, email, phone)            │
│  7. Completeness  (Objectives, Requirements,         │
│                    Constraints, Risks, NFRs)         │
└──────────────────────────┬───────────────────────────┘
                           │ validated + sanitized BRD
                           ▼
                  Orchestrator Agent
              (parses sections, builds routing map)
                           │
         ┌─────────────────┼──────────────────────┐
         │    ThreadPoolExecutor (parallel)        │
         ▼         ▼          ▼        ▼      ▼
    Plan Gen  Schedule   Architect   PoC   Tech Stack
    (RAG)     (RAG)      (RAG+Kroki) (RAG) (RAG)
         │         │          │        │      │
         └─────────┴──────────┴────────┴──────┘
                           │ PipelineState (5 typed outputs)
                           ▼
                    Critic Agent
               (LLM-as-Judge scoring)
                           │
            ┌──────────────┤
            │ FM-1: Hallucination Guard
            │   deducts 0.3/score per uncorroborated citation
            │ FM-2: Uncited Claim Cap
            │   caps score at 3.9 (Amber) if any agent has
            │   zero vector citations
            │ FM-3: Sentinel Fallback Cap
            │   caps at 3.9 + flags ConsistencyIssue if any
            │   agent returned a fallback mock structure
            └──────────────┤
                           │
              ┌────────────┴────────────┐
              │ score < threshold AND   │
              │ revision_count < 2?     │
              ▼ yes                     ▼ no
       Targeted Revision         HITL Approval Gate
       (failing agents only)     (Streamlit button
       → back to Critic           OR ElevenLabs voice)
                                        │
                  ┌─────────────────────┼──────────────────┐
                  ▼ Approved            ▼ Rejected          ▼ Pending
           ┌──────────────┐      Audit row only         (wait)
           │ Google Sheets │
           │ Jira Epic     │  ← MCP (mcp-atlassian stdio)
           │   (MCP → REST │    with REST fallback
           │    fallback)  │
           │ Pinecone BRD  │  ← ingests BRD for future RAG
           │   ingest      │
           │ PDF export    │  ← ReportLab
           └──────────────┘
```

---

## RAG Architecture

Each specialist agent retrieves organization-specific context from Pinecone before generating output.

**Ingestion (one-time setup):**
- Documents from `knowledge_base/` are split with a recursive character text splitter
- Embedded with `text-embedding-3-large` at 1024 dimensions
- Written to Pinecone with metadata: `source_type`, `chunk_id`, `source_file`

**Retrieval (per-agent, per-run):**
- Similarity threshold enforced at 0.45 — chunks below threshold are discarded
- Each specialist must return citations: `source_file` + `chunk_id` for every technical standard referenced
- Critic enforces citation presence and corroboration against known vector keys (FM-1, FM-2)

---

## Critic Revision Loop

The Critic evaluates four dimensions: Groundedness, Completeness, Consistency, and Actionability.

If the overall score falls below the threshold and fewer than 2 revision cycles have run, the Critic identifies which specific agents produced substandard output. Only those agents are re-invoked with targeted revision context. The full pipeline does not restart.

The loop is capped at 2 revision cycles. After 2 cycles, regardless of score, the pipeline proceeds to the HITL gate with the best available output and a flagged warning.

---

## HITL Gate

The Human-in-the-Loop gate supports two approval modes:

**UI mode:** The Streamlit interface displays the Critic's quality badge (Green/Amber/Red), full agent outputs, and the architecture diagram. The user approves or rejects via button.

**Voice mode:** ElevenLabs Conversational AI connects via webhook. The user can provide a numeric rating (1–5) and natural language feedback. The agent interprets the conversation and routes to approve or reject accordingly.

On approval, all four downstream integrations trigger: Google Sheets audit row, Jira Epic creation, Pinecone BRD ingestion, and PDF export.

---

## Failure Modes and Mitigations

| Failure | Mitigation |
|---|---|
| API timeout | `tenacity` exponential backoff (1s → 2s → 4s) |
| JSON parse failure | Schema recovery prompt; fallback to mock structure + FM-3 cap |
| Kroki.io down | Graceful fallback to client-side mermaid.js rendering |
| MCP server unavailable | Automatic fallback to Jira REST API; Epic still created |
| Google Sheets / Jira credentials missing | Skips gracefully; writes local CSV/zip to `logs/exports/` |
| Agent returns fallback mock | Critic FM-3 caps score at Amber, flags `ConsistencyIssue` in UI |

---

## Observability

Full trace visibility via **LangSmith**: every database call, agent dispatch, and LLM generation is traced with prompt structures, latency, model version, and token usage under the `em-copilot-brd-agent` project. Structured JSONL logs are simultaneously written locally to `logs/pipeline.jsonl`.

---

## What Is Not Shown Here

The following exist in the private repository:

- All agent prompts (Orchestrator, all 5 specialists, Critic)
- LangGraph state graph definition and routing logic
- RAG ingestion scripts and knowledge base documents
- Critic revision logic and FM-cap implementation
- Evaluation framework (`eval/run_eval.py`, calibration sets, ground-truth files)
- Integration code (Sheets, Jira MCP, ElevenLabs, PDF)
- Full Pydantic schema definitions (`src/core/models.py`)
