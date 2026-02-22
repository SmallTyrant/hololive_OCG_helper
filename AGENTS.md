# AGENT_PLAYBOOK.md

## Hololive OCG Helper – Claude-Optimized Swarm Architecture (Unified Edition)

---

# 1. Purpose

This playbook defines a Claude-efficient Swarm architecture that:

* Minimizes model usage (1–2 calls per PR)
* Prevents infinite fix loops
* Preserves auto-merge
* Runs release only via explicit label
* Protects DB and secrets
* Avoids full-repo scans and agent recursion

---

# 2. Global Safety Rules

* At most ONE code-modifying agent runs per PR.
* quality-gate runs once only.
* Automatic fix allowed once only.
* No recursive or chained agent loops.
* Release pipeline runs only when label "release" exists.
* Never bundle `data/hololive_ocg.sqlite` into Android/iOS builds.
* Never commit secrets (.p8, keystore, .env, credentials).
* No full-repo discovery scans.
* Prompts must remain under 15 lines.
* No coordinator agent.
* No planning agent.
* No parallel agent execution.

---

# 3. Repository Scope Map

Android runtime
`mobile/android/native/src/main/java/**/*.kt`

iOS runtime
`mobile/ios/native/Sources/**/*.swift`

Python runtime/tools
`app/**/*.py`
`tools/**/*.py`

Build/CI
`mobile/android/native-app/**`
`mobile/ios/native-app/**`
`scripts/**`
`.github/workflows/**`

---

# 4. Swarm Execution Model

## Development Flow

Issue created
→ Add scope label (`scope:android` | `scope:ios` | `scope:tools` | `scope:builder`)
→ Add label `go`
→ Language agent runs (1 Claude call)
→ CI runs
→ quality-gate runs (1 Claude call)
→ If tests pass → merge
→ If tests fail → fix once → CI → stop

No additional retries.

---

## Release Flow

Add label `release`
→ release-gate runs (1 Claude call)

Release never runs automatically without label.

---

# 5. Active Agents

---

## builder

Scope

* `mobile/android/native-app/**`
* `mobile/ios/native-app/**`
* `scripts/**`
* `.github/workflows/**`

Prompt Template

Role: builder
Goal: improve build/release stability only.
Scope: build scripts and CI only.

Rules:

* No runtime logic edits.
* No DB auto-bundling.
* Keep signing env-driven.
* Minimal diff.

Return:

* changed files
* reason
* build result
* risks

---

## kotlin

Scope

* `mobile/android/native/src/main/java/**/*.kt`

Prompt Template

Role: kotlin
Goal: safe Android runtime bug fix or optimization.

Rules:

* Preserve architecture.
* No Gradle/AGP/signing changes.
* Minimal change.

Return:

* changed files
* rationale
* test/build proof
* risks

---

## swift

Scope

* `mobile/ios/native/Sources/**/*.swift`

Prompt Template

Role: swift
Goal: safe iOS runtime bug fix or optimization.

Rules:

* Preserve user-visible behavior.
* No signing/build config changes.
* Minimal change.

Return:

* changed files
* improvement reason
* build/test proof
* risks

---

## python

Scope

* `app/**/*.py`
* `tools/**/*.py`

Prompt Template

Role: python
Goal: measurable low-risk improvement.

Rules:

* Preserve output behavior.
* Avoid repeated heavy work.
* No mobile code edits.

Return:

* targets
* implementation plan
* validation commands

---

## quality-gate

(Merged Review + Secret Guard)

Scope

* Current PR diff only

Prompt Template

Role: quality-gate
Goal: prevent regression and release risk.

Checks:

* correctness
* data safety
* build integrity
* secret patterns

Return:

* findings (high/medium/low)
* minimal fixes
* go/no-go

Runs once only.

---

## release-gate

(Release-only Agent)

Trigger
Label: `release`

Prompt Template

Role: release-gate
Goal: verify release readiness.

Tasks:

* Sync Android/iOS version fields
* Verify artifact presence and size
* Confirm DB not bundled
* Basic smoke summary

Return:

* release_status (success|failed)
* artifact summary
* blockers

---

# 6. Fix Policy (Strict Cost Control)

If CI fails:

* Run automatic fix once only.
* Add label `fix-attempted`.

If CI fails again:

* Add label `blocked`.
* Stop automation.

No further automatic retries.

---

# 7. Label System

scope:android → Android runtime work
scope:ios → iOS runtime work
scope:tools → Python/tools work
scope:builder → Build/CI work
go → Execute coding agent
tests-passed → CI success
tests-failed → CI failed
fix-attempted → One fix already attempted
blocked → Manual intervention required
release → Run release-gate

---

# 8. GitHub Workflow Trigger Rules

OpenCode execution trigger:

if: label == "go"

Auto merge trigger:

if: label == "tests-passed"

Fix trigger:

if: label == "tests-failed" AND not labeled "fix-attempted"

Release trigger:

if: label == "release"

---

# 9. Forbidden Patterns (Cost Explosions)

* Multi-agent parallel runs
* Planning agent before coding
* Review → rewrite → review loops
* Broad refactors
* Full repository analysis
* Auto-trigger on issue open
* Multi-scope PRs

---

# 10. Claude Call Budget

Coding → 1 call
Quality Gate → 1 call
Fix (optional) → 1 call
Release (optional) → 1 call

Typical PR: 1–2 calls only.

---

# 11. Operational Guidelines

* Keep PRs single-scope.
* Do not combine Android + iOS + Python in one issue.
* Always manually apply `go`.
* Use `release` only when artifacts are ready.
* Keep prompts minimal.
* Never include the full playbook inside runtime prompt.

---

# Final Outcome

This configuration:

* Reduces Claude usage by 60–80%
* Prevents infinite retry loops
* Maintains auto-merge
* Keeps release controlled
* Protects DB and secrets
* Keeps swarm deterministic and stable
