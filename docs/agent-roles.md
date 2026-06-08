# Agent Roles

EM Copilot is a 7-agent system. Each agent has a single, well-defined responsibility with a typed input/output contract. Agent prompts are proprietary. This document describes agent behavior at the conceptual level.

---

## Orchestrator Agent

**Model:** gpt-4o-mini  
**Pattern:** Hub-and-spoke dispatcher

**Responsibility:** Parse the validated BRD into structured sections (Objectives, Functional Requirements, Non-Functional Requirements, Constraints, Risks, Timeline). Build a routing map that assigns BRD sections to the appropriate specialist agents. Dispatch all five specialists concurrently via `ThreadPoolExecutor`.

**Input:** Sanitized BRD text (post-security-layer)  
**Output:** `OrchestratorOutput` — typed Pydantic model with parsed sections and routing assignments

**Prompt:** `[Orchestrator Agent Prompt — proprietary]`
> Purpose: Parse a raw BRD into structured sections and build a typed routing map for specialist agent dispatch. Handles malformed, incomplete, and ambiguous BRD structures.

---

## Plan Generator Agent

**Model:** gpt-4o  
**Pattern:** RAG + Reflection

**Responsibility:** Convert the BRD's functional and non-functional requirements into a phased engineering plan with milestones, owners, dependencies, and effort estimates. Uses Pinecone RAG to ground planning decisions in historical project data and org-specific planning templates. Each milestone must cite the vector chunks that informed it.

**Input:** Functional requirements section + RAG context  
**Output:** `EngineeringPlanOutput` — phases, milestones, owners, effort estimates, citations

**Prompt:** `[Plan Generator Agent Prompt — proprietary]`
> Purpose: Converts BRD requirements into a phased engineering plan grounded in retrieved org standards. Every milestone must reference a valid citation from the vector store.

---

## Schedule Estimator Agent

**Model:** gpt-4o  
**Pattern:** RAG + Timeline modeling

**Responsibility:** Map the engineering plan milestones to a sprint timeline with week-by-week estimates, dependency ordering, and team capacity assumptions. Uses RAG to reference historical delivery schedules for similar projects. Must flag milestones with high schedule risk.

**Input:** Engineering plan section + RAG context (historical schedules)  
**Output:** `ScheduleOutput` — sprint timeline, effort per milestone, risk flags, citations

**Prompt:** `[Schedule Estimator Agent Prompt — proprietary]`
> Purpose: Converts engineering milestones into a sprint-based delivery schedule grounded in historical velocity data from the vector store.

---

## Solution Architect Agent

**Model:** gpt-4o  
**Pattern:** RAG + Diagram synthesis

**Responsibility:** Design the system architecture for the BRD requirements and produce a Mermaid diagram representing the proposed architecture. Uses RAG to align architectural patterns with org standards. The Mermaid output is validated for syntax and then rendered to SVG via the Kroki API (with local mermaid.js fallback if Kroki is unavailable).

**Input:** Requirements + constraints section + RAG context (architectural patterns)  
**Output:** `ArchitectureOutput` — component descriptions, Mermaid diagram source, Kroki SVG (if rendered), citations

**Prompt:** `[Solution Architect Agent Prompt — proprietary]`
> Purpose: Produces a system architecture design aligned with org standards and renders it as a validated Mermaid diagram. Must cite all referenced architectural patterns.

---

## PoC Planner Agent

**Model:** gpt-4o  
**Pattern:** RAG + Scoping

**Responsibility:** Define a scoped Proof-of-Concept that de-risks the highest-uncertainty aspects of the engineering plan. Specifies PoC objectives, success criteria, timeline, and what risk is being reduced. Uses RAG to reference org-specific PoC templates and past PoC outcomes.

**Input:** Engineering plan + risks section + RAG context  
**Output:** `PoCOutput` — PoC objectives, success criteria, timeline, risk reduction mapping, citations

**Prompt:** `[PoC Planner Agent Prompt — proprietary]`
> Purpose: Scopes a targeted PoC that de-risks the highest-uncertainty elements of the plan, grounded in historical PoC outcomes from the vector store.

---

## Tech Stack Recommender Agent

**Model:** gpt-4o  
**Pattern:** RAG + Org context

**Responsibility:** Evaluate technology options for the proposed system against org standards, existing infrastructure, and team capabilities. Produces a structured set of recommendations with tradeoffs for each layer (API, data, infra, frontend). Uses RAG to retrieve org-approved technology lists and architectural decisions. GitHub API signals (activity, ecosystem health) augment recommendations where available.

**Input:** Architecture section + org constraints + RAG context  
**Output:** `TechStackOutput` — technology options by layer, tradeoffs, org alignment score, citations

**Prompt:** `[Tech Stack Recommender Agent Prompt — proprietary]`
> Purpose: Recommends technology options grounded in org standards and existing architecture decisions retrieved from the vector store. Flags deviations from org-approved choices.

---

## Critic Agent

**Model:** gpt-4o-mini  
**Pattern:** LLM-as-Judge with deterministic failure-mode caps

**Responsibility:** Evaluate the aggregated output of all five specialist agents across four dimensions. Route to targeted revision if quality is insufficient. Enforce three deterministic failure-mode caps that override LLM scoring to prevent optimism bias.

**Input:** Full `PipelineState` — all 5 specialist outputs + original requirements  
**Output:** `CriticOutput` — scores per dimension, overall score, quality badge, per-agent failure flags, revision routing decision

**Evaluation dimensions:**
- **Groundedness** — citations present and corroborated against vector DB keys
- **Completeness** — all BRD requirements addressed by at least one specialist
- **Consistency** — no contradictions across agents (e.g., 12-week schedule with 25-microservice architecture for a 2-engineer team)
- **Actionability** — outputs are specific enough to act on without further clarification

**Failure-mode caps (deterministic, override LLM scoring):**
- **FM-1 (Hallucination Guard):** Deducts 0.3 points per citation that does not match a known vector DB key
- **FM-2 (Uncited Claim Cap):** Caps overall score at 3.9 (Amber) if any specialist returned zero citations
- **FM-3 (Sentinel Fallback Cap):** Caps score at 3.9 and flags `ConsistencyIssue` in UI if any specialist returned a fallback mock structure due to API failure

**Prompt:** `[Critic Agent Prompt — proprietary]`
> Purpose: Audits all specialist outputs for groundedness, completeness, consistency, and actionability. Applies deterministic FM caps before finalizing scores. Routes to targeted revision or HITL gate.

---

## Agent Interaction Model

```
Orchestrator
     │ parallel dispatch (ThreadPoolExecutor)
     ├──► Plan Generator    ──┐
     ├──► Schedule Estimator  │ all outputs → PipelineState
     ├──► Solution Architect  │
     ├──► PoC Planner         │
     └──► Tech Stack       ──┘
                              │
                         Critic Agent
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
             Targeted Revision      HITL Gate
             (failing agents only)
```

All inter-agent communication uses typed Pydantic models. No agent receives raw text from another agent. Validation runs at every boundary before processing begins.
