"""
sanitized_example.py

End-to-end CLI walkthrough of the EM Copilot pipeline
using the sample BRD from samples/sample-brd.md.

Runs the mock 7-agent pipeline and prints formatted output.
No API keys or external dependencies required.

Usage:
    python demo/sanitized_example.py
    python demo/sanitized_example.py --verbose   # full task and tech stack detail
    python demo/sanitized_example.py --json      # raw JSON output
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mock_agent_runner import run_demo_pipeline, PipelineState

SAMPLE_BRD_PATH = Path(__file__).parent.parent / "samples" / "sample-brd.md"
DIV  = "─" * 72
DIV2 = "═" * 72


def load_brd() -> str:
    if SAMPLE_BRD_PATH.exists():
        return SAMPLE_BRD_PATH.read_text()
    return (
        "Build a real-time notification system. Users must receive in-app notifications "
        "within 2 seconds. Support 50,000 concurrent users. Allow per-type notification "
        "preferences. Push notifications for background users. Notification inbox with "
        "90-day history. Real-time badge counts in navigation. No existing WebSocket "
        "infrastructure. JWT auth system in place. Kafka event bus available."
    )


def print_security(state: PipelineState) -> None:
    s = state.security
    print(f"\n{'SECURITY LAYER  (7 checks)':^72}")
    print(DIV)
    for check, result in s.checks.items():
        icon = "✓" if result.startswith("pass") else "⚠" if result.startswith("warn") else "✗"
        print(f"  {icon}  {check:<30} {result}")
    if s.pii_redacted:
        print("  ⚠  PII was found and redacted before any LLM call")
    print(f"\n  Result: {'✓ PASSED — BRD cleared for LLM processing' if s.passed else '✗ FAILED — pipeline halted'}")


def print_orchestrator(state: PipelineState) -> None:
    o = state.orchestrator
    print(f"\n{'ORCHESTRATOR AGENT':^72}")
    print(DIV)
    print(f"  Sections parsed:   {len(o.sections)}")
    print(f"  FRs identified:    {len(o.sections.get('functional_requirements', []))}")
    print(f"  NFRs identified:   {len(o.sections.get('nfrs', []))}")
    print(f"  Open questions:    {len(o.open_questions)}")
    if o.open_questions:
        print()
        for q in o.open_questions:
            print(f"  ⚠  {q}")
    print(f"\n  Routing: {list(o.routing.keys())}")


def print_specialists(state: PipelineState, verbose: bool = False) -> None:
    print(f"\n{'SPECIALIST AGENTS  (parallel, ThreadPoolExecutor)':^72}")
    print(DIV)

    # Plan Generator
    plan = state.plan
    print(f"\n  Plan Generator   [{len(plan.citations)} citations]")
    print(f"  {plan.summary}")
    if verbose:
        for m in plan.milestones:
            phase_label = f"Phase {m.phase}"
            print(f"    [{m.id}] [{phase_label}] [{m.effort:2}]  {m.title}")
            print(f"           owners: {', '.join(m.owners)} | reqs: {', '.join(m.requirements)}")

    # Schedule Estimator
    sched = state.schedule
    print(f"\n  Schedule Estimator   [{len(sched.citations)} citations]")
    print(f"  Total weeks: {sched.total_weeks}  |  Sprints planned: {len(sched.sprint_plan)}")
    for flag in sched.risk_flags:
        print(f"  ⚠  {flag}")

    # Solution Architect
    arch = state.architecture
    kroki_status = "✓ SVG rendered" if arch.kroki_svg and "svg" in arch.kroki_svg.lower() else "⚠ fallback to mermaid.js"
    print(f"\n  Solution Architect   [{len(arch.citations)} citations]  Kroki: {kroki_status}")
    print(f"  Components: {', '.join(arch.components)}")
    if verbose:
        print(f"\n  Mermaid source:")
        for line in arch.mermaid_source.split("\n")[:8]:
            print(f"    {line}")
        print("    ...")

    # PoC Planner
    poc = state.poc
    print(f"\n  PoC Planner   [{len(poc.citations)} citations]")
    print(f"  Objective: {poc.objective[:80]}...")
    print(f"  Timeline: {poc.timeline_weeks} weeks  |  Risk reduced: {poc.risk_reduced}")
    if verbose:
        print("  Success criteria:")
        for c in poc.success_criteria:
            print(f"    • {c}")

    # Tech Stack
    tech = state.tech_stack
    print(f"\n  Tech Stack Recommender   [{len(tech.citations)} citations]")
    for opt in tech.options:
        aligned = "✓ org-aligned" if opt.org_aligned else "⚠ needs decision"
        print(f"  [{opt.layer:<25}]  {opt.recommendation:<30}  {aligned}")
        if verbose:
            print(f"    Tradeoff: {opt.tradeoff}")
            if opt.alternatives:
                print(f"    Alternatives: {', '.join(opt.alternatives)}")


def print_critic(state: PipelineState) -> None:
    c = state.critic
    badge_icon = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(c.badge, "·")
    print(f"\n{'CRITIC AGENT  (LLM-as-Judge + FM-1/2/3 caps)':^72}")
    print(DIV)

    scores = [
        ("Groundedness", c.groundedness),
        ("Completeness", c.completeness),
        ("Consistency",  c.consistency),
        ("Actionability", c.actionability),
    ]
    for dim, score in scores:
        bar_len = int(score / 5 * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {dim:<15} [{bar}] {score:.1f}/5.0")

    print(f"\n  Overall: {c.overall_score:.2f}/5.00   {badge_icon} {c.badge.upper()}")

    if c.fm_caps_applied:
        print()
        for cap in c.fm_caps_applied:
            print(f"  ⚠ FM cap applied: {cap}")

    if c.agent_flags:
        print()
        for flag in c.agent_flags:
            print(f"  ⚠ [{flag.severity.upper()}] {flag.agent}: {flag.issue}")

    revision_status = (
        f"Revision triggered (cycle {c.revision_count + 1}/2)" if c.revision_needed
        else "No revision needed — proceeding to HITL"
    )
    print(f"\n  Decision: {revision_status}")


def print_hitl(state: PipelineState) -> None:
    print(f"\n{'HITL APPROVAL GATE':^72}")
    print(DIV)
    print("  Mode: UI (Streamlit button) or Voice (ElevenLabs conversational agent)")
    if state.hitl_approved:
        print("  ✓ Approved — triggering downstream integrations:")
        print("    → Google Sheets  audit row written (CSV fallback if credentials missing)")
        print("    → Jira Epic      created via MCP (mcp-atlassian stdio → REST fallback)")
        print("    → Pinecone       BRD ingested for future RAG retrieval")
        print("    → PDF export     available at GET /download/{run_id}")
    elif state.hitl_approved is False:
        print("  ✗ Rejected — audit row written to Google Sheets only")
    else:
        print("  ⏳ Awaiting human input...")


def print_summary(state: PipelineState) -> None:
    c = state.critic
    plan = state.plan
    badge_icon = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(c.badge, "·")
    total_citations = sum([
        len(state.plan.citations),
        len(state.schedule.citations),
        len(state.architecture.citations),
        len(state.poc.citations),
        len(state.tech_stack.citations),
    ])
    print(f"\n{DIV2}")
    print(f"{'PIPELINE COMPLETE':^72}")
    print(DIV2)
    print(f"  BRD → Security → Orchestrator → 5 Specialists (parallel) → Critic → HITL")
    print()
    print(f"  Milestones planned:   {len(plan.milestones)}")
    print(f"  Total citations:      {total_citations} (across all 5 agents)")
    print(f"  Quality score:        {c.overall_score:.2f}/5.00  {badge_icon} {c.badge.upper()}")
    print(f"  Approved:             {'YES' if state.hitl_approved else 'NO'}")
    print(f"  Est. real cost:       ~$0.31 per run (GPT-4o specialists + GPT-4o-mini orchestrator/critic)")
    print(f"  Est. real runtime:    ~50s wall-clock (parallel dispatch vs >2.5min sequential)")
    print()
    print("  Sample outputs: samples/sample-engineering-plan.md")
    print("                  samples/sample-task-breakdown.md")
    print("  Architecture:   docs/architecture.md")
    print("  Live system:    https://huggingface.co/spaces/rganbote/em-copilot")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="EM Copilot — Demo Pipeline")
    parser.add_argument("--json",    action="store_true", help="Raw JSON output")
    parser.add_argument("--verbose", action="store_true", help="Full task and component detail")
    args = parser.parse_args()

    print(DIV2)
    print(f"{'EM Copilot — BRD to Engineering Plan Agent':^72}")
    print(f"{'7-Agent LangGraph Pipeline (Mock Demo)':^72}")
    print(DIV2)
    print()
    print("  Loading BRD: Real-Time Notification System v1.2")
    print("  Running pipeline...\n")

    brd_text = load_brd()
    state = run_demo_pipeline(brd_text)

    if args.json:
        # Convert to JSON-serializable form (dataclasses → dicts)
        def to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {k: to_dict(v) for k, v in asdict(obj).items()}
            if isinstance(obj, list):
                return [to_dict(i) for i in obj]
            return obj
        print(json.dumps(to_dict(state), indent=2, default=str))
        return

    print_security(state)
    print_orchestrator(state)
    print_specialists(state, verbose=args.verbose)
    print_critic(state)
    print_hitl(state)
    print_summary(state)


if __name__ == "__main__":
    main()
