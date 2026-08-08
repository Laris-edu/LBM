---
name: lbm-doc-sync
description: >-
  Sync the LBM project's documentation after any state-changing action — finishing a
  run/diagnostic, recording a decision, changing phase or P2-x test status, or producing
  new files/directories. Updates PROJECT_CONTEXT.md (thin entry doc), the current
  Phase_N/PhaseN_STATUS.md (detailed log), and folder README.md / Phase2_Output_Files_Guide.md
  per the hybrid-layered doc architecture. Use whenever documentation could drift from
  code/run state — doc sync, update context, update status, after a run, new file output,
  phase transition.
---

# LBM documentation sync (hybrid-layered architecture)

During project execution, **every change to code / runs / decisions MUST be synced to the
documentation in the same change set**. This skill is the sync checklist.

## Layered document responsibilities (iron rule: every fact has exactly ONE home — no duplication, no bloat)

> The architecture rationale and the "which home does a fact belong to" decision rules live
> in `docs/Doc_Architecture.md`.

| Document | Responsibility | What does NOT belong here |
|---|---|---|
| `docs/PROJECT_CONTEXT.md` | The project's single **entry point**: conclusions, interpretation guardrails, links | run details, full numbers, derivations, long tables |
| `docs/Phase_N/PhaseN_STATUS.md` (current: `docs/Phase_5/Phase5_STATUS.md`) | The current phase's **detailed ledger**: run records, numbers, changelog, risks | — |
| Per-directory `README.md` (code/config dirs) | **File-by-file** index local to that directory | cross-directory relationships |
| `docs/Phase_N/PhaseN_Output_Files_Guide.md` (current: `Phase5_Output_Files_Guide.md`) | **Cross-directory overview**: structure map, topic-doc index, run-output/archive conventions, implementation boundaries | file-by-file tables (those live in directory READMEs; keep pointers only) |

## Checklist

### 1. Decide whether the sync is triggered
Does this change hit ANY of the following (a hit makes updating the entry doc and the phase
status MANDATORY; the authoritative trigger list is `PROJECT_CONTEXT.md` §7):
- A phase completed/started, or the current-phase pointer changed
- An M2/M3/M4/M5-level decision changed; a new authoritative run exists
- A key test status changed (P2-4/5/6/7/9 or any later-phase gate/test)
- collision / unit mapping / heat-flux definition / bulk-viscosity policy / lattice-scaling changed
- Phase-entry scope or Level A/B/C boundaries changed
- The next-step priority changed

### 2. Update the entry doc `docs/PROJECT_CONTEXT.md`
Check and update at least: `最后更新` (last-updated), the minimal new-session reading list,
current phase & status, the no-misread rules, current key decisions, next-step priority.
**Keep it thin** — run numbers and derivations go into STATUS, never backfilled into the
entry doc.

### 3. Update the phase status `docs/Phase_N/PhaseN_STATUS.md`
Append this run / conclusion / numbers to the ledger and the changelog; register new
scripts or documents in the relevant section.

### 4. File outputs → place them per the hybrid layering
- **New or changed files in a code/config directory** → update that directory's
  `README.md` file-by-file table.
- **New cross-directory topic document** (closure/acoustic/robustness/gate-report class)
  → update the current phase's `Output_Files_Guide` index and docs structure map, and file
  it under the right subdirectory.
- **New results run** → archive convention: `results/` is never committed (`.gitignore`);
  the digest goes into the relevant verification/gate report; for long-term retention copy
  the curated summary set (summary.json + report md — no h5/figures) into the current
  phase's archive directory (current: `archive/M5_runs/`; legacy example:
  `archive/M2_runs/`).
- **When a directory README is created or backfilled**: degrade the corresponding
  file-by-file table inside the `Output_Files_Guide` to a pointer, so the two copies
  cannot drift apart.

### 5. Moving / renaming files
- Use `git mv` to preserve history.
- Grep for ALL cross-references and sync them: paths inside docs, script `--report-out`/
  `--out` defaults, `python -m scripts.X` invocations in docs, `from scripts.X import`
  in tests.
- Remember `scripts/` is a FLAT namespace package (scripts import each other as
  `scripts.X` and are imported by tests) — **never move scripts into subdirectories**;
  categorize via name prefixes + `scripts/README.md`.

### 6. Verify
- Every referenced path exists (grep check, zero dead links).
- If code was touched, run the affected tests (at minimum
  `verification/test_phase1_reference_data_integrity.py` plus whatever the change touches).
- Report to the user which documents this sync changed. **Commits / PRs remain under the
  user's control unless explicitly requested.**
