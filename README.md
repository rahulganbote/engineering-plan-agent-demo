# EM Copilot: BRD to Engineering Plan Agent (Demo)

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-green)](https://github.com/langchain-ai/langgraph)
[![Pinecone](https://img.shields.io/badge/RAG-Pinecone-purple)](https://pinecone.io)
[![LangSmith](https://img.shields.io/badge/Observability-LangSmith-orange)](https://smith.langchain.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)](https://streamlit.io)
[![Jira](https://img.shields.io/badge/Jira%20Epic-MCP%20%2B%20REST-0052CC)](https://www.atlassian.com/software/jira)
[![ElevenLabs](https://img.shields.io/badge/Voice%20HITL-ElevenLabs-1F1F1F)](https://elevenlabs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A demo of **EM Copilot**: a Multi-Agent AI system, orchestrated with LangGraph and grounded with RAG, that transforms a raw Business Requirements Document (BRD) into a draft engineering package: structured plan, project schedule, architecture diagram, PoC definition, and tech stack options. Outputs are evaluated by a Critic Agent, downloadable as PDF, reviewed via a Human-in-the-Loop (HITL) gate supporting Voice commands, and deployed to Jira Cloud, Google Sheets dashboards, and Slack alerts.

🔗 **Live Demo:** [EM-Copilot on Google Cloud](https://em-copilot-809545615573.us-east4.run.app/)

---

## Table of Contents

1. [Business Use Case & Solution](#business-use-case--solution)
   * [The Challenge](#the-challenge)
   * [The EM Copilot Solution](#the-em-copilot-solution)
2. [What This Demo Repository Shows](#what-this-demo-repository-shows)
3. [Architectural Overview](#architectural-overview)
4. [System Design & Core Pillars](#system-design--core-pillars)
   * [Core Capabilities](#core-capabilities)
   * [Agent Inventory](#agent-inventory)
5. [Tech Stack Justification](#tech-stack-justification)
6. [Token Usage & Execution Cost](#token-usage--execution-cost)
7. [Evaluation Framework](#evaluation-framework)
   * [Evaluation Results (v0 → v1)](#evaluation-results-v0--v1)
8. [Screenshots of Demo](#screenshots-of-demo)
9. [Challenges & Lessons Learned](#challenges--lessons-learned)
10. [Project Directory Structure](#project-directory-structure)
11. [Quick Start Guide](#quick-start-guide)
12. [Note on Completeness](#note-on-completeness)
13. [License](#license)
14. [Author](#author)

---

## Business Use Case & Solution

### The Challenge

Engineering Managers face a persistent bottleneck translating complex BRDs into structured technical plans, schedules, and architecture diagrams. This manual process is time-consuming and produces inconsistent results:

- **Delivery delays**: Weeks spent drafting sprint scopes and mapping timelines
- **Misalignment**: Gaps between business intent and engineering implementation
- **Inconsistent scoping**: Ad-hoc architectures and planning criteria varying across squads
- **Org-specific tech stacks**: Evaluating technology stacks relative to what is supported and allowed vs unsupported at the organizational level

### The EM Copilot Solution

EM Copilot ingests a raw BRD and produces a complete, audit-ready engineering bundle in under ~60 seconds, reducing the administrative timeline for kickoffs significantly (~25%-50%). The system combines RAG-grounded specialist Agents with a self-correcting Critic loop and human approval gate, so outputs carry a clear Green / Amber / Red quality badge before anything reaches Jira or Google Sheets.

---

## What This Demo Repository Shows

| Area | What You Can See |
|---|---|
| System Architecture | 7-agent design, parallel dispatch, Critic loop, HITL gate |
| Security Pipeline | 7-check deterministic validation layer before any LLM call |
| Agent Roles | Each agent's responsibility, input/output contract, design pattern |
| Evaluation Framework | 5-method eval with v0→v1 benchmark improvement data |
| Sample Input/Output | Realistic BRD → full engineering plan + task breakdown |
| Mock Demo Code | Pipeline structure and data contracts without real prompts |
| Demo Screenshots | Streamlit UI and LangSmith telemetry traces |
| Cost Analysis | Token breakdown and cost per pipeline run (~$0.31/run) |

---

## Architectural Overview


```
                         ┌─────────────────────────────────────────────────┐
                         │         SECURITY VALIDATION LAYER               │
BRD Upload ──► FastAPI──►│  File check → Parse → Injection Guard (regex)   │
(Streamlit)     POST     │  → Injection Guard (LLM) → PII Redact → BRD ✓   │
            run-pipeline └─────────────────────────────────────────────────┘
                                              │ validated BRD text
                                              ▼
                                    Orchestrator Agent
                                    (hub — parses, routes sections)
                                              │
                                              ▼
            ┌─────────────────────────────────────────────────────────────────────────┐
            │ ThreadPoolExecutor │ (parallel dispatch) │             │                │
            ▼                    ▼                     ▼             ▼                ▼
    Plan Generator    Schedule Estimator  Solution Architect  PoC Planner  Tech Stack Recommender
    (RAG + Reflect)   (RAG + Timelines)   (RAG + Diagram)   (RAG + Timelines) (RAG + Org Stds)
            │                     │    (Mermaid+Kroki) │                 │           │ 
            ▼                     ▼                    ▼                 ▼           ▼ 
            └─────────────────────└────────────────────────┘─────────────────└───────────┘
                                    │                       
                                    ▼       ◄──── all 5 outputs together  
                             Critic Agent  
                            (LLM-as-judge + FM-1/2/3 caps)
                                    │
                     ┌──────────────┴───────────────┐
                     │  score < threshold?          │
                     │  revision_count < 2?         │
                     ▼ yes                          ▼ no
              ↻ Targeted revision           HITL Approval Gate
              (only flagged Agents)         (Button OR Voice via ElevenLabs)
                                                    │
                        ┌───────────────────────────┼───────────────────────────┐
                        │                           │                           │
                        ▼ Approved                  ▼ Rejected                  ▼
          Sheets + Jira Epic (MCP) + Pinecone   Sheets audit row only              (wait)
```
<!--
![EM Copilot LangGraph Pipeline](diagrams/langgraph_pipeline_flow.png)
-->
See [diagrams/README.md](diagrams/README.md) for node-by-node annotation.
The diagram shows the full LangGraph hub-and-spoke pipeline: security layer → orchestrator hub → threaded fan-out to 5 parallel specialist agents → Pydantic fan-in → Critic (LLM-judge + FM caps) → decision router → HITL gate → downstream integrations. 

---

## System Design & Core Pillars

### Core Capabilities

- **7-agent LangGraph pipeline**: Hybrid Hub-and-Spoke design pattern. Parallel dispatch to specialist agents is ~3× faster than sequential chaining (~50s vs >2.5 minutes).
- **Pydantic-enforced output contracts**: Clean execution at every agent boundary with zero untyped LLM handoffs.
- **Deterministic security layer**: A 7-step safety pipeline (format, size, word count, regex injection guard, semantic injection guard, PII redaction, completeness check) that runs before any LLM execution.
- **Pinecone RAG**: Each specialist agent retrieves org-specific standards with citation tracking; the Critic enforces that citations match valid vector chunks.
- **LLM-as-Judge Critic with 3 deterministic failure-mode caps**: Prevents the Critic from being overly optimistic (Hallucination guard, uncited claim cap, sentinel fallback cap).
- **Targeted revision loop**: The Critic flags only the specialist agents that failed; only those nodes re-run (max 2 cycles), avoiding full graph replays.
- **ElevenLabs Voice HITL Gate**: Conversational human approval accepting numeric ratings and natural language feedback via webhook.
- **Jira Epic via MCP**: Uses the `mcp-atlassian` MCP server (stdio transport) with automatic fallback to REST API; constructs descriptions in Atlassian Document Format (ADF).
- **5-method evaluation framework**: Rule-based, LLM-as-Judge, execution/schema validation, BERTScore semantic diffs, and Human HITL ratings.
- **LangSmith full-trace observability**: Every model call, token count, prompt structure, and latency captured.

### Agent Inventory

| Agent | Model | Role | Pattern |
|---|---|---|---|
| **Orchestrator** | GPT-4o-mini | Parses BRD sections, routes to specialists | Hub-and-spoke dispatcher |
| **Plan Generator** | GPT-4o | Creates phased engineering plan with milestones | RAG + Reflection |
| **Schedule Estimator** | GPT-4o | Estimates effort, sprint timeline, dependencies | RAG + Timeline modeling |
| **Solution Architect** | GPT-4o | Generates Mermaid diagram rendered via Kroki | RAG + Diagram synthesis |
| **PoC Planner** | GPT-4o | Defines proof-of-concept scope and success metrics | RAG + Scoping |
| **Tech Stack Recommender** | GPT-4o | Evaluates technology options against org standards | RAG + Org standards |
| **Critic Agent** | GPT-4o-mini | Quality auditing, revision loop control, Rule-based + BERTScore | LLM-as-Judge |

---

## Tech Stack Justification

| Category | Technology | Engineering Reason |
|---|---|---|
| **Agent State** | LangGraph v0.2.28 | State Graph model with native routing, cycle tracking, and async interrupts |
| **Vector DB** | Pinecone Serverless | Fully managed index with fast cosine-similarity search over technical standards |
| **Embeddings** | `text-embedding-3-large` (1024) | High dimensionality with customized text projection for dense architectural guides |
| **Models** | GPT-4o (specialists) + GPT-4o-mini (critic) | Balance between specialist reasoning quality and critic execution cost |
| **Web Server** | FastAPI | Async endpoints, Server-Sent Events (SSE) for UI streaming, and non-blocking exports |
| **Frontend UI** | Streamlit | Rapid UI prototyping displaying real-time execution graphs and progress logs |
| **Voice Interface** | ElevenLabs Conversational AI | Webhook integration executing natural language HITL discussion & approvals |
| **Tool Integration** | Model Context Protocol (MCP) | Standardized Agent-to-Tool transport; the Jira Epic push runs through an `mcp-atlassian` server spawned over stdio |
| **Resilience Primitives** | Custom `src/core/resilience.py` (mirrors Hystrix / Polly / resilience4j) | Small surface area, no external dependency; per-instance state with frozen `CallPolicy` |
| **Cache Backends** | `InMemoryCache` / `RedisCache` / `TieredCache` / `SemanticBackend` (Pinecone) | Pluggable `CacheBackend` Protocol — chosen at runtime via `init_default_backend_from_env()` |
| **Event Bus** | Lightweight `src/core/events.py` emitter | Best-effort event fan-out for `cache_hit`, `cache_miss`, `retry`, `breaker_open`, `bulkhead_timeout`; surfaced into Streamlit SSE stream |

---

## Token Usage & Execution Cost

| Agent | Model | Est. Cost |
|---|---|---|
| Security + Orchestrator + Critic | gpt-4o-mini | ~$0.003 |
| Plan Generator | gpt-4o | ~$0.063 |
| Schedule Estimator | gpt-4o | ~$0.043 |
| Solution Architect | gpt-4o | ~$0.075 |
| PoC Planner | gpt-4o | ~$0.043 |
| Tech Stack Recommender | gpt-4o | ~$0.043 |
| **Total per run** | | **~$0.31** |

---

## Evaluation Framework

### Evaluation Results (v0 → v1)

| Dimension | v0 (Initial) | v1 (Post-Critic) | Delta |
|---|---|---|---|
| Groundedness | 2.40 | 3.90 | +1.50 |
| Completeness | 3.80 | 4.80 | +1.00 |
| Consistency | 4.10 | 4.60 | +0.50 |
| Actionability | 3.20 | 4.00 | +0.80 |
| **Overall** | **3.38 / 5.00 🟡** | **4.33 / 5.00 🟢** | **+0.95** |

---

## Screenshots of Demo

See [screenshots/README.md](screenshots/README.md) from sample run.

---
## Challenges & Lessons Learned

Building a production-grade Multi-Agent system surfaces problems that simple PoC demos may not. Below are the key lessons grouped by engineering focus:

### System Reliability, Security & Observability
* **Reliable AI over complexity:** Fewer bells and whistles and more reliable execution leads to higher adoption. Hardening the Critic, evaluation methods, and the security layer produced a far more reliable system.
* **Guardrails & compliance:** LLMs are susceptible to prompt injection. Asking agents to "cite sources" for grounding is not enough; the Critic must actively verify that citations map back to real vector chunk keys.
* **Telemetry from Day 1:** Silent failures are common in production Agent systems. Telemetry like LangSmith is mandatory from the beginning because you cannot debug or fix what you cannot trace.
* **Cost & token governance:** Full-scale LangSmith monitoring is expensive. A production architecture should sample traces for new releases or red-flagged runs, while letting local structured JSONL logs handle routine telemetry.

### Data Strategy & Evaluation Frameworks
* **Data strategy & Golden datasets:** Requires thorough analysis of schemas and data consumed. Output quality is only as good as the Golden dataset. Defining Pydantic structures at the org level prevents schema drift, and golden datasets must be version-controlled.
* **Overcoming optimistic LLM-as-Judge behavior:** LLM judges are optimistic by default. Autonomous components need guardrails wrapped *around* them, not embedded *inside* them (e.g., wrapping the Critic with deterministic rules like BERTScore).
* **Responsible AI & HITL:** Autonomous agents require a mindset shift. Hallucination detection requires active enforcement—nothing exports without a Human-in-the-Loop approval gate (e.g., Jira tickets are created only upon explicit human approval).

### Architecture, Latency & Product Design
* **Modular vs. functional design:** Extensibility is easily missed, and mid-project refactoring is expensive. Explicitly provide the "Big Picture" in the BRD and future roadmap, not just the task spec.
* **Latency is a product experience:** A 50-second wait time is fast for complex generation, but users expect immediate feedback. Parallel dispatch yielded the biggest latency improvement (3× speedup) through orchestration optimization.
* **Conversational AI & HITL complexity:** Getting voice assistants to interpret complex artifact summaries requires highly structured prompt context. Budget extra development cycles for integrating voice-based human feedback.

---

## Project Directory Structure

To navigate this public demo repository, here is the layout of the system design documents, sample outputs, and simulated execution scripts:

```
engineering-plan-agent-demo/
├── README.md
├── docs/
│   ├── architecture.md              # 7-agent system design and patterns
│   ├── system-flow.md               # Step-by-step pipeline walkthrough
│   ├── agent-roles.md               # Agent responsibilities and contracts
│   └── security-and-sanitization.md # What's protected and why
├── diagrams/
│   ├── README.md                    # Mermaid source for diagrams
│   └── langgraph_pipeline_flow.png   # LangGraph pipeline flow diagram
├── screenshots/
│   ├── README.md                    # Detailed annotations for screenshots
│   ├── 01-streamlit-pipeline-green.png
│   ├── 02-streamlit-artifacts-architecture.png
│   ├── 03-hitl-voice-elevenlabs.png
│   ├── 04-langsmith-trace-nodes.png
│   ├── 05-langsmith-tracing-list.png
│   ├── 06-langsmith-monitoring.png
│   └── 07-langsmith-cost-tokens.png
├── samples/
│   ├── sample-brd.md                # Realistic BRD input
│   ├── sample-engineering-plan.md   # Full generated plan output
│   └── sample-task-breakdown.md     # Task breakdown by engineering domain
├── demo/
│   ├── mock_agent_runner.py         # Simulated 7-agent pipeline (no real prompts)
│   ├── requirements.txt             # Demo python dependencies
│   └── sanitized_example.py         # End-to-end CLI walkthrough
└── LICENSE
```

---
> [!NOTE]
> **Mock vs. Production Code:** This repository showcases the architectural design and data flows using a structural mock pipeline (`demo/mock_agent_runner.py`). No API keys or external credentials are required to run this demo locally. The full production implementation is hosted in a private repository to protect intellectual property.

---

## Quick Start Guide

```bash
git clone https://github.com/rahulganbote/engineering-plan-agent-demo.git
cd engineering-plan-agent-demo
python demo/sanitized_example.py            # formatted output
python demo/sanitized_example.py --verbose  # include task detail
python demo/sanitized_example.py --json     # raw JSON output
```

No API keys required. The demo runs the pipeline structure over mock data.

---

## Note on Completeness

This is a **demo repository**. The core implementation—including detailed prompts, orchestrator graphs, RAG ingestion scripts, and integration logic—resides in a private repository to protect intellectual property.

🔒 **Private Repository:** [github.com/rahulganbote/engineering-plan-agent](https://github.com/rahulganbote/engineering-plan-agent)

This demo is designed to illustrate system architecture, output quality, and engineering design. I am happy to walk through the implementation details one-on-one.

---

## License
MIT License - Feel free to use this project for learning and inspiration.

---

## Author

**Rahul Ganbote** — [LinkedIn](https://www.linkedin.com/in/rahul-ganbote-040a7b/) · [GitHub @rahulganbote](https://github.com/rahulganbote)

---

*© 2026 Rahul Ganbote · All rights reserved.*
