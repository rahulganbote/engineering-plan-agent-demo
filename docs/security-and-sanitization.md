# Security and Sanitization

## Why This Repo Is a Demo

This repository is a public-facing demo of EM Copilot, which is maintained in a private repository. This document explains what has been included, what has been excluded, and the reasoning behind each decision.

---

## What Is Included

| Content | Included | Reason |
|---|---|---|
| README with problem/solution/highlights | ✅ | Recruiter and hiring manager visibility |
| Full system architecture with real tech stack | ✅ | Shows design quality without implementation |
| All 7 agent role descriptions with patterns | ✅ | Conceptual depth without prompt exposure |
| 7-check security pipeline description | ✅ | Shows security thinking |
| 5-method evaluation framework + benchmark results | ✅ | Shows measurement rigor |
| Cost per run breakdown | ✅ | Shows production-readiness thinking |
| Realistic sample BRD input | ✅ | Shows realistic input handling |
| Full sample engineering plan + task breakdown | ✅ | Shows output quality and format |
| Mock demo code (7-agent structure, no real prompts) | ✅ | Shows pipeline design |
| Architecture and flow diagrams | ✅ | Visual system understanding |

---

## What Is Excluded

| Content | Excluded | Reason |
|---|---|---|
| All agent prompts | ❌ | Core IP — months of iterative engineering |
| LangGraph state graph and routing logic | ❌ | Custom orchestration architecture |
| Critic revision logic and FM-cap implementation | ❌ | Proprietary quality enforcement system |
| RAG ingestion scripts and knowledge base | ❌ | Org-specific content and pipeline design |
| Evaluation framework (`eval/run_eval.py`, calibration sets, ground-truth files) | ❌ | Proprietary eval methodology |
| Integration code (Sheets, Jira MCP, ElevenLabs, PDF) | ❌ | Full implementation detail |
| Pydantic schema definitions (`src/core/models.py`) | ❌ | Precise output contracts |
| API keys, credentials, `.env` | ❌ | Standard security practice |
| Git history from private repo | ❌ | Repo created fresh — no history leakage |

---

## How Prompts Are Referenced

Where prompts are conceptually relevant, this repo uses placeholder blocks:

```
[Agent Name Prompt — proprietary]
Purpose: Plain-English description of what the prompt does and what it must enforce.
```

This gives readers enough context to understand each agent's role and constraints without exposing the actual prompt engineering.

---

## How Demo Code Is Structured

The demo code in `demo/` simulates the pipeline structure using typed dataclasses and mock data. It shows:

- The 7-agent pipeline structure (Orchestrator, 5 specialists, Critic)
- Input/output data contracts at each step
- The sequence of agent calls and state passing
- The Critic scoring and revision routing logic (structure only)
- The downstream integration trigger pattern

It does **not** show:
- Real prompts or prompt construction
- Real LLM API calls
- LangGraph state graph or routing
- Actual Pinecone retrieval
- Critic FM-cap logic implementation
- Any integration code

---

## Security Pipeline in the Real System

The 7-check security layer runs before any LLM node processes the document:

1. **Format restriction** — `.txt`, `.pdf`, `.docx` only
2. **Size guard** — ≤ 10MB hard limit
3. **Word count** — ≥ 50 words required
4. **Regex injection scan** — 15 known jailbreak/injection patterns
5. **LLM semantic scan** — gpt-4o-mini for sophisticated multi-paragraph injections
6. **PII redaction** — SSN, credit card, email, phone replaced with `[REDACTED-*]` placeholders
7. **Completeness check** — Objectives, Requirements, Constraints, Risks, NFRs presence verified

The security layer implementation (`src/security/validator.py`) is in the private repository.

---

## Repo Creation Approach

This repo was created fresh from a clean folder — not by copying the private repo and deleting files. This ensures:

- No commit history from the private repo is present or recoverable
- No deleted files, configs, or internal artifacts are accessible
- A clean public record showing only what was intentionally published

---

## For Hiring Managers

If you're evaluating this system and want to understand the full implementation — prompt design, LangGraph orchestration, Critic logic, evaluation methodology, or integration architecture — I'm happy to walk through it in a technical interview or design review.

The separation between public demo and private implementation is a deliberate engineering decision, not an attempt to obscure weak work. The live system is accessible at [huggingface.co/spaces/rganbote/em-copilot](https://huggingface.co/spaces/rganbote/em-copilot).
