# Parallel Agent Quality Loop

This repository uses a repeatable delivery loop:

1. Apply code changes.
2. Run automated checks.
3. If checks fail, analyze root cause.
4. Apply targeted fix.
5. Re-run checks.
6. Review diff and finalize commit/PR.

## Local Run (repeatable)

Use `scripts/run_quality_loop.py` to run checks in parallel and retry.

```bash
python3 scripts/run_quality_loop.py --max-attempts 3
```

Optional auto-fix hook (for an external agent command):

```bash
python3 scripts/run_quality_loop.py --max-attempts 3 --fix-command "<your-fix-command>"
```

Artifacts are written to:

- `.artifacts/quality-loop/attempt-XX/*.log`
- `.artifacts/quality-loop/attempt-XX/report.json`

Python syntax check uses `scripts/python_syntax_check.py` and skips build/output directories.

## CI Run (parallel)

Workflow: `.github/workflows/quality-loop.yml`

- `python_checks`, `android_checks`, and `ios_checks` run in parallel.
- `analyze_failures` aggregates logs and classifies errors using `scripts/analyze_ci_failures.py`.
- Workflow fails if any required check fails.

## Parallel Agent Model

For large tasks, split work by scope and run agents in parallel:

- Agent A: `app/**`, `tools/**`, `scripts/**` (rules/data/tools)
- Agent B: `mobile/android/**`
- Agent C: `mobile/ios/**`
- Agent D: verification/log analysis (`scripts/analyze_ci_failures.py`)
- Agent E: final diff review and PR write-up

Recommended merge order:

1. Rules/data/tooling
2. Android/iOS runtime changes
3. Verification and docs

## Commit/PR Unit Rules

- Keep commits small and scoped.
- Include automated result summary in each PR.
- If a failure occurred, include root cause and re-fix notes.
- Do not merge without final diff review.
