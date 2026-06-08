# Diagrams

Architecture and flow diagrams for EM Copilot.

## architecture_hub_spoke_v3.svg — LangGraph Pipeline (Hub-and-Spoke)

![EM Copilot LangGraph Pipeline](architecture_hub_spoke.png)

This is the actual architecture diagram showing:
- **Deterministic Security Layer** — 7 checks before any LLM node runs
- **`node_orchestrator_hub`** — BRD parsing and section routing
- **`node_dispatch_specialists`** — Threaded Fan-Out via `ThreadPoolExecutor` (5 agents in parallel)
- **5 Specialist Agents** — RAG-grounded, Pydantic output contracts
- **`node_aggregate_outputs`** — Pydantic Fan-In collecting all specialist results
- **`node_critic`** — LLM-judge over 4 dimensions + FM-1/2/3 deterministic caps
- **`node_decision_router`** — routes to HITL gate, targeted revision loop, or error node
- **`await_hitl`** — LangGraph interrupt/pause point for human review
- **HITL Gate** — ElevenLabs Voice or UI button approval
- **Downstream** — ReportLab PDF, Pinecone KB ingest, Jira Cloud MCP, Google Sheets export

Node names shown (`node_orchestrator_hub`, `node_dispatch_specialists`, etc.) are the LangGraph graph node identifiers — these reflect the pipeline structure but do not include prompts or orchestration logic.

---

## high-level-architecture.png — Mermaid source

```mermaid
flowchart TD
    A[BRD Upload\nStreamlit UI] --> SEC

    subgraph SEC [Security Layer — 7 checks]
        S1[Format] --> S2[Size] --> S3[Words] --> S4[Regex Inject]
        S4 --> S5[LLM Inject] --> S6[PII Redact] --> S7[Completeness]
    end

    SEC --> ORCH[Orchestrator Agent\ngpt-4o-mini]

    ORCH --> PX

    subgraph PX [Parallel Dispatch — ThreadPoolExecutor]
        PG[Plan Generator\ngpt-4o + RAG]
        SE[Schedule Estimator\ngpt-4o + RAG]
        SA[Solution Architect\ngpt-4o + RAG + Kroki]
        PP[PoC Planner\ngpt-4o + RAG]
        TS[Tech Stack\ngpt-4o + RAG]
    end

    PX --> CR[Critic Agent\ngpt-4o-mini\nLLM-as-Judge + FM-1/2/3]
    CR -->|score < threshold\nrevision_count < 2| PX
    CR -->|proceed| HITL[HITL Approval Gate\nUI or ElevenLabs Voice]

    HITL -->|Approved| OUT

    subgraph OUT [Downstream Integrations]
        D1[Google Sheets\naudit row]
        D2[Jira Epic\nMCP → REST fallback]
        D3[Pinecone\nBRD ingestion]
        D4[PDF Export\nReportLab]
    end
```

## multi-agent-flow.png

```mermaid
sequenceDiagram
    participant User
    participant Streamlit
    participant FastAPI
    participant Security
    participant Orchestrator
    participant Specialists
    participant Pinecone
    participant Critic
    participant HITL
    participant Jira

    User->>Streamlit: Upload BRD
    Streamlit->>FastAPI: POST /run-pipeline
    FastAPI->>Security: 7-check validation
    Security-->>FastAPI: validated + sanitized BRD
    FastAPI->>Orchestrator: parsed BRD
    Orchestrator-->>FastAPI: routing map
    FastAPI->>Specialists: parallel dispatch (5 agents)
    Specialists->>Pinecone: RAG retrieval (per agent)
    Pinecone-->>Specialists: relevant chunks + citations
    Specialists-->>FastAPI: typed outputs (PipelineState)
    FastAPI->>Critic: full PipelineState
    Critic-->>FastAPI: scores + badge + FM caps + decision
    FastAPI->>HITL: display for human review
    HITL-->>FastAPI: approve
    FastAPI->>Jira: create Epic (MCP → REST fallback)
    FastAPI-->>User: PDF download + Sheets audit row
```

## Rendering Options

**GitHub** renders Mermaid natively in Markdown — paste the code blocks into any `.md` file.

**Excalidraw / draw.io** — use for polished PNG exports.

**CLI render:**
```bash
npx @mermaid-js/mermaid-cli -i diagrams/architecture.mmd -o diagrams/high-level-architecture.png
```
