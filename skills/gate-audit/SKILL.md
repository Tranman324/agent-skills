---
name: gate-audit
description: "Use when a PR needs a merge-gate review. Runs three independent audits (spec, bugs, adversarial) against one pinned commit."
license: MIT
platforms: [linux, macos]
---

# Gate Audit

## When to Use

Triggers: gate audit, PR gate review, pre-merge review, squash-merge review, release gate.

**Read the full playbook before every audit:** `references/gate-audit-playbook.md`.

**Prerequisites:** the exact repo, base ref, commit to audit, and spec; Git; and a sub-agent tool that can run independent read-and-report contexts in parallel. Choose models per lens (see below). If you can't get the reviewers or models the audit needs, report the audit as blocked instead of quietly running a weaker one.

## Quick Reference

Every gate audit runs **3 independent sessions** against the same pinned commit:

| Session | Lens | Suggested model tier |
|---------|------|----------------------|
| 1: Spec Compliance | Does the code match the spec? Deviations, missing features, copy mismatches | Mid-tier is usually enough (mechanical comparison) |
| 2: Bug Hunting | What's broken? Races, null paths, access-control gaps, state-machine holes | Strongest available |
| 3: Adversarial | What breaks in production? Abuse, edge cases, cascading failures, bad assumptions | Strongest available |

**All 3 finish before any fix ships.** One consolidated findings doc, organized by severity:
- 🔴 **Critical:** fix before merge
- 🟡 **Should Fix:** high value
- 🟠 **Minor:** fix or defer with a written reason
- ⚪ **Defensive Gap:** no bug today, breaks under stress

## Procedure

1. **Preflight before spawning anything.** In the repo, resolve base and commit to full hashes with `git rev-parse --verify <ref>^{commit}`. Require an empty `git status --porcelain` and a non-empty `git diff <base>...<commit> --stat`. Capture the diff stat and `git log <base>..<commit> --oneline` once, for every prompt. Stop on a dirty tree, bad ref, or empty diff. Never auto-commit or discard someone's changes.
2. **Build self-contained prompts.** Each reviewer gets the resolved hashes, captured diff and log, spec, relevant repo rules, its lens, its concern area, the severity definitions, and the output contract. Session 2 prompts include the **full code-smell baseline and its rules** from the playbook.
3. **Split big codebases by concern, not file count.** Two sub-agents per session is a good default. Use scoped context packs; after the first full pass, audit only changed files plus their direct dependencies. Encode fixed bugs as regression tests. Session 3 builds a state × event table with expected vs actual behavior.
4. **Dispatch independently.** Run reviewers concurrently. Reviewers read and report only: no edits, fixes, merges, or releases. **No pre-approved deferrals;** reviewers find gaps on their own. Never seed one lens with another lens's findings.
5. **Wait for everyone.** Cap each report at about 400 words of findings (quotes and line refs count; preamble doesn't). A missing or failed reviewer means the audit is incomplete. Keep each finding's severity and lens tag. **Never rerank across lenses,** and never drop or demote a finding because another lens found something bigger.
6. **Write the artifacts.** Every doc states the pinned hash. Raw reports go to `tmp/gate-{N}-session-{1a,1b,2a,2b,...}-report.md`; the single `tmp/gate-{N}-consolidated-findings.md` (by severity, with file paths, line numbers, and lens tags) is the handoff to implementation. It is not permission to fix, merge, or release.

## Verification and Pitfalls

Record the playbook path, resolved base and commit, clean-tree and non-empty-diff evidence, reviewer IDs, the models actually used, each report's completion, and the final findings path. Check that every doc carries the same hash, every concern area and all three lenses are covered, the taxonomy is intact, and nothing was reranked across lenses. Keep superseded gate docs instead of overwriting history. A pre-mortem can decide where to spend review time; it never demotes a finding.
