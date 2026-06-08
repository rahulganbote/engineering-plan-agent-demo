"""
mock_agent_runner.py

Simulated 7-agent pipeline for the EM Copilot demo.

Demonstrates the structure, data contracts, and agent sequencing of the
real system without exposing prompts, LangGraph orchestration, or
Pinecone RAG implementation.

In the real system, each function here is replaced by a LangGraph node
that invokes a GPT-4o or GPT-4o-mini agent with a proprietary prompt,
retrieves RAG context from Pinecone, and returns a validated Pydantic model.

Real pipeline: LangGraph · GPT-4o (specialists) · GPT-4o-mini (orchestrator/critic)
               Pinecone RAG · LangSmith telemetry · FastAPI backend · Streamlit UI
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Pydantic-style dataclasses (simplified versions of the real schemas)
# In the real system: src/core/models.py with full Pydantic validation
# ---------------------------------------------------------------------------

@dataclass
class Citation:
    source_file: str
    chunk_id: str
    relevance_score: float


@dataclass
class SecurityResult:
    passed: bool
    checks: dict  # check_name -> pass/fail/warn
    pii_redacted: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class OrchestratorOutput:
    sections: dict
    routing: dict
    open_questions: list[str] = field(default_factory=list)


@dataclass
class Milestone:
    id: str
    title: str
    phase: int
    effort: str  # S, M, L, XL
    owners: list[str]
    requirements: list[str]
    citations: list[Citation] = field(default_factory=list)


@dataclass
class EngineeringPlanOutput:
    summary: str
    milestones: list[Milestone] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)


@dataclass
class SprintWeek:
    week: int
    milestone_id: str
    tasks: list[str]
    team: str


@dataclass
class ScheduleOutput:
    total_weeks: int
    sprint_plan: list[SprintWeek] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)


@dataclass
class ArchitectureOutput:
    components: list[str]
    mermaid_source: str
    kroki_svg: Optional[str]  # None if Kroki unavailable (falls back to mermaid.js)
    citations: list[Citation] = field(default_factory=list)


@dataclass
class PoCOutput:
    objective: str
    success_criteria: list[str]
    timeline_weeks: int
    risk_reduced: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class TechOption:
    layer: str
    recommendation: str
    alternatives: list[str]
    tradeoff: str
    org_aligned: bool


@dataclass
class TechStackOutput:
    options: list[TechOption] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)


@dataclass
class AgentFlag:
    agent: str
    issue: str
    severity: str  # high, medium, low


@dataclass
class CriticOutput:
    groundedness: float
    completeness: float
    consistency: float
    actionability: float
    overall_score: float
    badge: str  # green (≥4.0), amber (3.0–3.9), red (<3.0)
    fm_caps_applied: list[str]
    agent_flags: list[AgentFlag]
    revision_needed: bool
    agents_to_revise: list[str]
    revision_count: int


@dataclass
class PipelineState:
    """Aggregated state passed through the LangGraph pipeline."""
    brd_text: str
    security: Optional[SecurityResult] = None
    orchestrator: Optional[OrchestratorOutput] = None
    plan: Optional[EngineeringPlanOutput] = None
    schedule: Optional[ScheduleOutput] = None
    architecture: Optional[ArchitectureOutput] = None
    poc: Optional[PoCOutput] = None
    tech_stack: Optional[TechStackOutput] = None
    critic: Optional[CriticOutput] = None
    revision_count: int = 0
    hitl_approved: Optional[bool] = None


# ---------------------------------------------------------------------------
# Security layer mock
# Real system: src/security/validator.py — 7 sequential deterministic checks
# ---------------------------------------------------------------------------

def security_layer_mock(brd_text: str) -> SecurityResult:
    """
    [Security Layer — proprietary implementation]
    7-check sequential pipeline: format, size, word count, regex injection,
    LLM semantic injection, PII redaction, completeness check.
    """
    word_count = len(brd_text.split())
    return SecurityResult(
        passed=True,
        checks={
            "format_check": "pass",
            "size_guard": "pass",
            "word_count": f"pass ({word_count} words)",
            "regex_injection_scan": "pass (0/15 patterns matched)",
            "llm_injection_scan": "pass (gpt-4o-mini: no injection detected)",
            "pii_redaction": "pass (0 PII instances found)",
            "completeness_check": "pass (all required sections present)",
        },
        pii_redacted=False,
    )


# ---------------------------------------------------------------------------
# Orchestrator mock
# Real system: src/agents/orchestrator.py — gpt-4o-mini
# ---------------------------------------------------------------------------

def orchestrator_agent_mock(brd_text: str) -> OrchestratorOutput:
    """
    [Orchestrator Agent Prompt — proprietary]
    Purpose: Parses BRD into typed sections and builds a routing map
    for concurrent specialist dispatch.
    """
    return OrchestratorOutput(
        sections={
            "objectives": "Deliver real-time in-app notifications within 2 seconds...",
            "functional_requirements": ["FR-001", "FR-002", "FR-003", "FR-004", "FR-005"],
            "nfrs": ["NFR-001: 50k concurrent users", "NFR-002: p99 < 5s", "NFR-003: no perf regression"],
            "constraints": ["No existing WebSocket infra", "JWT auth in place", "Kafka event bus exists"],
            "risks": ["Scale target unvalidated", "Push provider not selected", "Mobile capacity unconfirmed"],
        },
        routing={
            "plan_generator": ["functional_requirements", "nfrs"],
            "schedule_estimator": ["functional_requirements", "constraints"],
            "solution_architect": ["functional_requirements", "nfrs", "constraints"],
            "poc_planner": ["risks", "functional_requirements"],
            "tech_stack": ["constraints", "nfrs"],
        },
        open_questions=[
            "Push notification provider not specified (blocks FR-003)",
            "Rate limiting threshold per user not defined",
            "Notification retention policy not stated",
        ],
    )


# ---------------------------------------------------------------------------
# Specialist agent mocks (run concurrently in real system)
# Real system: src/agents/ — each uses gpt-4o + Pinecone RAG
# ---------------------------------------------------------------------------

def plan_generator_mock(orchestrator_output: OrchestratorOutput) -> EngineeringPlanOutput:
    """
    [Plan Generator Agent Prompt — proprietary]
    Purpose: Converts BRD requirements into a phased engineering plan
    grounded in Pinecone-retrieved org standards. Every milestone must
    cite at least one valid vector chunk.
    """
    return EngineeringPlanOutput(
        summary="Phase 1 (Q1): WebSocket infrastructure, preferences, badge counts. "
                "Phase 2 (Q2): Push notifications, notification inbox.",
        citations=[
            Citation("past_projects/messaging_platform_2023.md", "chunk_047", 0.71),
            Citation("engineering_standards/milestone_templates.md", "chunk_012", 0.82),
        ],
        milestones=[
            Milestone("M1", "WebSocket Infrastructure and Real-Time Delivery", phase=1,
                      effort="XL", owners=["backend", "infra"],
                      requirements=["FR-001", "NFR-001", "NFR-002"],
                      citations=[Citation("past_projects/messaging_platform_2023.md", "chunk_047", 0.71)]),
            Milestone("M2", "Notification Preference Service", phase=1,
                      effort="M", owners=["backend", "frontend"],
                      requirements=["FR-002"],
                      citations=[Citation("planning_guidelines/effort_estimation.md", "chunk_003", 0.68)]),
            Milestone("M3", "Real-Time Badge Counts", phase=1,
                      effort="S", owners=["frontend"],
                      requirements=["FR-005"],
                      citations=[Citation("engineering_standards/milestone_templates.md", "chunk_012", 0.82)]),
            Milestone("M4", "Push Notification Integration", phase=2,
                      effort="L", owners=["backend", "mobile"],
                      requirements=["FR-003"],
                      citations=[Citation("past_projects/push_notification_2022.md", "chunk_019", 0.74)]),
            Milestone("M5", "Notification Inbox", phase=2,
                      effort="M", owners=["backend", "frontend"],
                      requirements=["FR-004"],
                      citations=[Citation("engineering_standards/milestone_templates.md", "chunk_015", 0.79)]),
        ],
    )


def schedule_estimator_mock(orchestrator_output: OrchestratorOutput) -> ScheduleOutput:
    """
    [Schedule Estimator Agent Prompt — proprietary]
    Purpose: Maps milestones to a sprint timeline grounded in historical
    delivery velocity data from the Pinecone vector store.
    """
    return ScheduleOutput(
        total_weeks=20,
        sprint_plan=[
            SprintWeek(1, "M1", ["WS lifecycle spec", "Infra audit"], "backend+infra"),
            SprintWeek(2, "M1+M2", ["JWT auth at WS handshake", "Preference data model"], "backend"),
            SprintWeek(3, "M1", ["Connection manager (single node)"], "backend"),
            SprintWeek(4, "M1", ["Routing schema", "Horizontal scaling design"], "backend+infra"),
            SprintWeek(5, "M1", ["Horizontal scaling impl (Redis pub/sub)"], "backend"),
            SprintWeek(6, "M1+M2", ["Dispatch API (Kafka→WS)", "Preference API"], "backend"),
            SprintWeek(7, "M1+M2+M3", ["Load test 10k", "Preference UI", "Badge component"], "all"),
            SprintWeek(8, "M1+M2+M3", ["Load test 50k", "Preference enforcement", "Badge WS connect"], "all"),
            SprintWeek(9, "M1+M2+M3", ["Integration testing", "Perf regression tests"], "QA"),
            SprintWeek(10, "M1+M2+M3", ["Hardening + buffer"], "all"),
        ],
        risk_flags=[
            "M1 go/no-go gate at week 8 (50k load test) — must pass before Q1 launch",
            "M4 cannot begin until push provider decided — escalate week 1",
            "Mobile team Q1 capacity unconfirmed — M4 token registration needs Q1 bandwidth",
        ],
        citations=[Citation("past_projects/messaging_platform_2023.md", "chunk_052", 0.77)],
    )


def solution_architect_mock(orchestrator_output: OrchestratorOutput) -> ArchitectureOutput:
    """
    [Solution Architect Agent Prompt — proprietary]
    Purpose: Designs system architecture aligned with org standards and
    produces a validated Mermaid diagram rendered via Kroki API.
    """
    mermaid = """
graph TD
    Client[Client Browser/App]
    LB[Load Balancer<br/>WebSocket-aware]
    WSM[WebSocket Manager<br/>Connection Pool]
    Redis[(Redis Pub/Sub<br/>Cross-node sync)]
    Dispatch[Notification Dispatcher]
    Kafka[(Kafka Event Bus<br/>Notification triggers)]
    PrefSvc[Preference Service]
    PrefDB[(User Preferences DB)]
    PushSvc[Push Notification Service]
    FCM[Push Provider<br/>FCM / APNs]

    Client -->|WS connect + JWT| LB
    LB --> WSM
    WSM <-->|pub/sub| Redis
    Kafka --> Dispatch
    Dispatch --> PrefSvc
    PrefSvc <--> PrefDB
    PrefSvc -->|filtered| WSM
    PrefSvc -->|push eligible| PushSvc
    PushSvc --> FCM
    FCM --> Client
    """.strip()

    return ArchitectureOutput(
        components=[
            "WebSocket Manager (horizontal, Redis pub/sub)",
            "Notification Dispatcher (Kafka consumer)",
            "Preference Service (filter layer)",
            "Push Notification Service (FCM / APNs)",
            "WebSocket-aware Load Balancer",
        ],
        mermaid_source=mermaid,
        kroki_svg="<svg><!-- Kroki-rendered SVG would appear here --></svg>",
        citations=[Citation("architectural_patterns/realtime_systems.md", "chunk_008", 0.85)],
    )


def poc_planner_mock(orchestrator_output: OrchestratorOutput) -> PoCOutput:
    """
    [PoC Planner Agent Prompt — proprietary]
    Purpose: Scopes a targeted PoC that de-risks the highest-uncertainty
    elements of the plan, grounded in historical PoC outcomes.
    """
    return PoCOutput(
        objective="Validate that a single-node WebSocket connection manager can sustain "
                  "10,000 concurrent connections within latency SLA before committing to "
                  "horizontal scaling architecture.",
        success_criteria=[
            "p99 message delivery latency < 500ms at 10k concurrent connections",
            "Zero cross-user message delivery in any test run",
            "Connection stability > 99.9% over 30-minute sustained load test",
            "Memory usage per connection < 50KB",
        ],
        timeline_weeks=2,
        risk_reduced="NFR-001 scale feasibility — validates architectural approach before M1 full build",
        citations=[Citation("past_projects/poc_outcomes_2023.md", "chunk_031", 0.72)],
    )


def tech_stack_recommender_mock(orchestrator_output: OrchestratorOutput) -> TechStackOutput:
    """
    [Tech Stack Recommender Agent Prompt — proprietary]
    Purpose: Recommends technology options grounded in org standards and
    existing architecture decisions. Flags deviations from org-approved choices.
    """
    return TechStackOutput(
        options=[
            TechOption("Real-time transport", "WebSocket (native)", ["SSE", "Long polling"],
                       "WebSocket required for bidirectional badge count updates (FR-005). SSE is read-only.", True),
            TechOption("Cross-node sync", "Redis Pub/Sub", ["Kafka fan-out", "Shared DB polling"],
                       "Redis Pub/Sub is low-latency and already in org infra. Kafka fan-out adds complexity.", True),
            TechOption("Push provider", "Firebase Cloud Messaging (FCM)", ["Apple APNs direct", "OneSignal", "Expo"],
                       "FCM unifies iOS+Android+Web push. Requires provider decision from product. Org has no existing preference.", False),
            TechOption("Event source", "Existing Kafka event bus", ["New event service"],
                       "Existing Kafka bus is org standard. No new event infrastructure needed.", True),
        ],
        citations=[
            Citation("engineering_standards/approved_tech_stack.md", "chunk_004", 0.88),
            Citation("engineering_standards/infra_guidelines.md", "chunk_011", 0.76),
        ],
    )


# ---------------------------------------------------------------------------
# Critic mock
# Real system: src/agents/critic.py — gpt-4o-mini + deterministic FM caps
# ---------------------------------------------------------------------------

def critic_agent_mock(state: PipelineState) -> CriticOutput:
    """
    [Critic Agent Prompt — proprietary]
    Purpose: Audits all specialist outputs for groundedness, completeness,
    consistency, and actionability. Applies deterministic FM-1/2/3 caps
    before finalizing scores. Routes to targeted revision or HITL gate.

    FM-1 (Hallucination Guard): -0.3 per uncorroborated citation
    FM-2 (Uncited Claim Cap): cap at 3.9 if any agent has zero citations
    FM-3 (Sentinel Fallback Cap): cap at 3.9 if any agent returned mock structure
    """
    # Verify all agents have citations (FM-2 check)
    agents_with_citations = {
        "plan_generator": len(state.plan.citations) > 0,
        "schedule_estimator": len(state.schedule.citations) > 0,
        "solution_architect": len(state.architecture.citations) > 0,
        "poc_planner": len(state.poc.citations) > 0,
        "tech_stack": len(state.tech_stack.citations) > 0,
    }
    all_cited = all(agents_with_citations.values())

    raw_scores = {
        "groundedness": 3.9,
        "completeness": 4.8,
        "consistency": 4.6,
        "actionability": 4.0,
    }
    overall_raw = sum(raw_scores.values()) / len(raw_scores)

    fm_caps = []
    if not all_cited:
        overall_raw = min(overall_raw, 3.9)
        uncited = [a for a, cited in agents_with_citations.items() if not cited]
        fm_caps.append(f"FM-2: {', '.join(uncited)} returned zero citations — score capped at 3.9")

    overall = round(overall_raw, 2)
    badge = "green" if overall >= 4.0 else "amber" if overall >= 3.0 else "red"

    return CriticOutput(
        groundedness=raw_scores["groundedness"],
        completeness=raw_scores["completeness"],
        consistency=raw_scores["consistency"],
        actionability=raw_scores["actionability"],
        overall_score=overall,
        badge=badge,
        fm_caps_applied=fm_caps,
        agent_flags=[],
        revision_needed=(overall < 4.0 and state.revision_count < 2),
        agents_to_revise=[],
        revision_count=state.revision_count,
    )


# ---------------------------------------------------------------------------
# Pipeline runner (simulates LangGraph state machine)
# Real system: src/agents/pipeline.py — LangGraph StateGraph
# ---------------------------------------------------------------------------

def run_demo_pipeline(brd_text: str) -> PipelineState:
    """
    Runs the mock 7-agent pipeline over the provided BRD text.

    Simulates the LangGraph state machine structure:
    Security → Orchestrator → Parallel dispatch → Critic → [Revision] → HITL

    In the real system, this is the LangGraph StateGraph definition in
    src/agents/pipeline.py with async interrupts, retry wrappers, and
    full LangSmith telemetry.
    """
    state = PipelineState(brd_text=brd_text)

    # Step 1: Security validation
    print("→ [Security Layer]     Running 7-check validation pipeline...")
    state.security = security_layer_mock(brd_text)
    if not state.security.passed:
        print("  ✗ Security validation failed — pipeline halted")
        return state
    print(f"  ✓ All checks passed")

    # Step 2: Orchestrator
    print("→ [Orchestrator]       Parsing BRD and building routing map...")
    state.orchestrator = orchestrator_agent_mock(brd_text)
    print(f"  ✓ {len(state.orchestrator.sections)} sections parsed, "
          f"{len(state.orchestrator.open_questions)} open questions flagged")

    # Step 3: Parallel specialist dispatch
    print("→ [Parallel Dispatch]  Running 5 specialist agents concurrently...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            "plan":       executor.submit(plan_generator_mock, state.orchestrator),
            "schedule":   executor.submit(schedule_estimator_mock, state.orchestrator),
            "architect":  executor.submit(solution_architect_mock, state.orchestrator),
            "poc":        executor.submit(poc_planner_mock, state.orchestrator),
            "tech_stack": executor.submit(tech_stack_recommender_mock, state.orchestrator),
        }
        state.plan        = futures["plan"].result()
        state.schedule    = futures["schedule"].result()
        state.architecture = futures["architect"].result()
        state.poc         = futures["poc"].result()
        state.tech_stack  = futures["tech_stack"].result()

    total_citations = sum([
        len(state.plan.citations),
        len(state.schedule.citations),
        len(state.architecture.citations),
        len(state.poc.citations),
        len(state.tech_stack.citations),
    ])
    print(f"  ✓ All 5 agents complete | {len(state.plan.milestones)} milestones | "
          f"{total_citations} total citations")

    # Step 4: Critic evaluation (with FM caps)
    print("→ [Critic Agent]       Evaluating outputs (LLM-as-Judge + FM caps)...")
    state.critic = critic_agent_mock(state)
    badge_icon = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(state.critic.badge, "·")
    print(f"  {badge_icon} Score: {state.critic.overall_score}/5.00  Badge: {state.critic.badge.upper()}")
    if state.critic.fm_caps_applied:
        for cap in state.critic.fm_caps_applied:
            print(f"  ⚠ FM cap: {cap}")

    # Step 5: Targeted revision if needed
    if state.critic.revision_needed:
        print(f"→ [Revision Loop]      Revising: {state.critic.agents_to_revise} (cycle {state.revision_count + 1}/2)...")
        state.revision_count += 1
        # In real system: only flagged agents re-run, then Critic re-evaluates

    print("→ [HITL Gate]          Awaiting human approval (UI or voice)...")
    state.hitl_approved = True  # auto-approved in mock
    print(f"  ✓ Approved — triggering: Google Sheets, Jira Epic (MCP), Pinecone ingest, PDF export")

    return state


if __name__ == "__main__":
    sample_brd = (
        "Build a real-time notification system. Users must receive in-app notifications "
        "within 2 seconds. Support 50,000 concurrent users. Allow per-type notification "
        "preferences. Push notifications for background users. Notification inbox with "
        "90-day history. Real-time badge counts in navigation. No existing WebSocket "
        "infrastructure. JWT auth system in place. Kafka event bus available."
    )
    result = run_demo_pipeline(sample_brd)
    print(f"\nPipeline complete. Milestones: {len(result.plan.milestones)}, "
          f"Score: {result.critic.overall_score}/5.00 {result.critic.badge.upper()}")
