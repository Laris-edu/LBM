---
name: lbm-run-discipline
description: >-
  Launch and babysit long-running LBM compute safely — background/detached runs,
  authoritative gate runs, process pools, multi-hour settles, temp/scratch outputs.
  Use BEFORE launching any run expected to outlive the current turn (background job,
  detached process, schtasks, Start-Process, overnight/authoritative run) and when
  writing large temporary outputs. Covers: no interactive REPL with redirected stdio,
  post-launch log verification, per-case checkpointing against power loss, detach
  mechanics per machine, scratchpad hygiene. Triggers: launch run, background run,
  long run, detached process, overnight run, checkpoint, scratchpad, temp files.
---

# LBM run-execution discipline

Hard-won operational rules for launching compute that outlives the session. Each rule
below was paid for with a real incident; do not relearn them.

## 1. Never run interactive Python with redirected stdio

**Incident (2026-08-09 cleanup of 2026-08-01/02 session)**: a diagnostic was launched
as an interactive interpreter with stdout redirected to a file. On Windows, Python
3.13+ PyREPL probes the console (`getheightwidth()`); with no real TTY it raises
`WinError` and its recovery loop **retries forever**, printing the identical traceback
at disk-write speed. Result: a single 174 GB text file of one repeated traceback in
the session scratchpad, discovered a week later on the user's system drive.

- Always `python script.py` (project `.venv`, explicit script argument).
- Never bare `python`, never `python < script > out`, never anything that can fall
  into a REPL in a background/detached/redirected context. `-c` one-liners and
  heredocs to `python -` are fine ONLY in foreground tool calls with bounded output.

## 2. Verify the log within minutes of any launch

A launch is not "done" when the process starts. Within the first minutes, read the
log file and confirm: (a) it grows at the expected rate (KB/min for progress lines,
not MB/s), (b) the content is the expected protocol lines, not a repeating error.
A byte-rate explosion or a repeated traceback means kill the process immediately.

Related, pre-existing: write long-command output to a log FILE and read the file —
never pipe through `tail` in the launch command; truncation lets a traceback eat the
result lines (P4-1 lesson, twice).

## 3. Multi-hour pooled runs MUST checkpoint per case

**Incident (2026-08-08/09)**: an overnight power loss killed an authoritative run
whose 14 finished cases (~5 h of compute) lived only in the parent process memory —
total loss; only the log survived. `execute_cases` accumulates results in memory and
the runner writes files at the END by default.

- Any run whose wall clock exceeds ~1 h must persist each completed case atomically
  (tmp + `os.replace`) with an identity stamp (protocol scalars + config digest +
  input-state digest) and skip identity-matching checkpoints on relaunch.
- Reference implementation: `scripts/phase5_wp4_jacobian_ablation.py`
  (`_checkpoint_wrap`, `checkpoints/<mode>_<cfgsha>/`). Orchestration-layer only —
  the per-case physics path stays untouched (same discipline family as the
  serial/parallel A/B rule for pools).
- Do not assume uptime: the A machine has had one unexplained mid-run shutdown under
  sustained all-core load (2026-08-08 night). Resilience over optimism.

## 4. Detach mechanics per machine

- **A machine (local)**: `Start-Process -WindowStyle Hidden` with
  `-RedirectStandardOutput/-RedirectStandardError` to files under
  `results/.../logs/`. Survives harness/session restarts (proven 2026-08-08).
  Session-tied background shells die with the session — do not use them for
  multi-hour runs.
- **B machine (ssh)**: `schtasks` one-shot dispatch; `Start-Process` dies with the
  ssh session (measured, WP4 dispatch). Create ONCE tasks with an already-past
  `/ST` (a future `/ST` re-fires — the A1 23:59 replay incident) and delete the
  task definition after the run. Both machines: same commit before dispatch,
  machine fingerprint into provenance (D5-3).
- **Win11 EcoQoS throttling (B, measured 2026-08-09)**: schtasks-launched python
  ran at ~6% duty — Windows 11 power-throttles BelowNormal/background processes
  onto parked E-cores on hybrid CPUs. Fix (persistent, per-exe):
  `powercfg /powerthrottling disable /path <base-python.exe>` AND the venv
  `python.exe`, then verify duty via two `TotalProcessorTime` samples (~99%
  expected). Post-launch duty verification is part of rule 2 on any newly
  provisioned machine.

## 5. Scratchpad hygiene

The session scratchpad is a temp area nobody revisits after the session ends —
garbage left there persists indefinitely on the user's machine.

- Delete intermediates > ~100 MB as soon as their purpose is served, and sweep the
  scratchpad before wrapping up a session.
- Anything worth keeping does not belong in the scratchpad: run products go to
  `results/` (untracked), curated summaries to `archive/` per the archive
  conventions, conclusions to the docs layer (then run `/lbm-doc-sync`).
