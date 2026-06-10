# Repo Knowledge And Agent Memory Implementation Plan

> **For Copilot:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Turn the completed paper-trading scaffold into an easier repo to navigate, document, and operate with repeatable agent context.

**Architecture:** Keep generated graph outputs, curated docs, and agent memory separate. Graphify provides broad repository navigation, docs explain stable architecture and workflows, and scoped agent memory/customization files give future coding sessions short task-specific context without loading the whole repo.

**Tech Stack:** Graphify, Markdown, VS Code custom instructions, GitHub PR workflow, Python 3.12, React/TypeScript dashboard.

---

## Task 1: Generate Repository Knowledge Graph

**Files:**
- Create/Update: `graphify-out/GRAPH_REPORT.md`
- Create/Update: `graphify-out/graph.json`
- Create/Update: `graphify-out/wiki/index.md`

**Step 1: Run Graphify on the repository**

Run:
```bash
/graphify . --wiki
```

Expected: Graphify detects the Python backend, React dashboard, docs, and planning files, then writes report, graph JSON, and wiki output.

**Step 2: Review the audit trail**

Check `graphify-out/GRAPH_REPORT.md` for EXTRACTED, INFERRED, and AMBIGUOUS edges.

Expected: Ambiguous edges are either accepted as useful or noted for follow-up.

**Step 3: Decide whether to track graph output**

Generated graph output may be large. Decide whether to commit the report/wiki only, commit all graph artifacts, or keep graph output local.

Expected: The repo has an explicit decision before graph artifacts are added to git.

## Task 2: Curate Operator Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Create: `docs/operator-runbook.md`

**Step 1: Add an operator runbook**

Document local setup, research run, RALPH smoke run, dashboard launch, Alpaca MCP account-clock helper, and kill-switch behavior.

Expected: A new contributor can operate the demo without reading source first.

**Step 2: Tighten architecture documentation**

Update the architecture doc with the RALPH loop, event spine, store, API, dashboard, and paper-only broker boundaries.

Expected: The doc reflects the implemented system, not only the initial research scaffold.

**Step 3: Link docs from README**

Add links to the runbook, architecture doc, implementation plan, and Graphify report if committed.

Expected: README remains short while pointing to deeper docs.

## Task 3: Add Scoped Agent Memory

**Files:**
- Create: `CLAUDE.md` or project-level equivalent only if wanted for this repo
- Create: `.memory/decisions.md`
- Create: `.memory/patterns.md`
- Create: `.memory/inbox.md`
- Optional Create: `src/stock_trade/CLAUDE.md`
- Optional Create: `dashboard/CLAUDE.md`
- Optional Create: `docs/CLAUDE.md`

**Step 1: Draft root routing context**

Keep the root context under 60 lines and route agents to backend, dashboard, and docs contexts.

Expected: Future sessions load only relevant scoped context.

**Step 2: Record durable decisions**

Capture paper-only default, no live adapter, explicit execution gates, read-only MCP defaults, and Graphify artifact policy.

Expected: Safety decisions survive chat context loss.

**Step 3: Add scoped context files only where useful**

Create directory-level context for backend, dashboard, and docs if it reduces repeated file reading.

Expected: No broad always-on memory bloat.

## Task 4: Add VS Code Agent Customization

**Files:**
- Modify: `.github/copilot-instructions.md`
- Optional Create: `.github/instructions/python-trading.instructions.md`
- Optional Create: `.github/instructions/dashboard-ui.instructions.md`
- Optional Create: `.github/agents/verifier.agent.md`

**Step 1: Keep global repo instructions concise**

Ensure the always-on instruction file stays focused on trading safety, secrets, and module boundaries.

Expected: Instructions help every task without burning context on implementation details.

**Step 2: Add file-scoped instructions if patterns repeat**

Use targeted `applyTo` globs for backend trading code, tests, and dashboard UI if future work needs stronger local guidance.

Expected: Scope-specific guidance loads only when relevant.

**Step 3: Add a verifier agent only if useful**

Create a repo-local verifier agent for quality gates if repeated PR verification becomes routine.

Expected: Verification remains deterministic and does not expose secrets.

## Task 5: Push Planning Updates

**Files:**
- Modify: this plan as tasks complete

**Step 1: Verify docs-only changes**

Run:
```bash
git diff --check
```

Expected: No whitespace errors.

**Step 2: Commit and push**

Run:
```bash
git add docs/plans/2026-06-02-repo-knowledge-and-agent-memory.md
git commit -s -m "docs: Plan repository knowledge workflow"
git push
```

Expected: The open PR includes this planning track.

## Definition Of Done

- The repo has a clear decision on whether Graphify artifacts are tracked.
- Operator docs cover local research, dashboard, MCP account status, and safety gates.
- Agent memory is scoped and concise if added.
- VS Code customization files use precise descriptions and `applyTo` patterns.
- The GitHub PR contains the implementation scaffold plus the next planning track.