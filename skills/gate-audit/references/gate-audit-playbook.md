# Gate Audits: Adversarial QA Standard

*For every PR gate review. Three sessions, three lenses.*

## Prerequisites

The exact repo, base ref, commit, and spec; Git; and a sub-agent tool that runs independent contexts in parallel. Pick models per lens (see Structure). If the reviewers or models the audit needs aren't available, report the audit as blocked and get the owner's approval for any substitute. Don't quietly downgrade. Normal permissions and approvals still apply.

## Structure

Every gate audit runs 3 independent sessions against the same commit:

| Session | Lens | Suggested model tier | Question |
|---------|------|----------------------|----------|
| **Session 1: Spec Compliance** | Does the code match the spec? | Mid-tier | Find deviations, missing features, copy mismatches |
| **Session 2: Bug Hunting** | What's broken? | Strongest available | Race conditions, null paths, access-control gaps, state-machine holes |
| **Session 3: Adversarial Exploration** | What breaks in production? | Strongest available | Edge cases, abuse vectors, cascading failures, design assumptions |

**All 3 sessions finish before any fix ships.** One consolidated fix list, not three rounds of fixes.

## Preflight (fail fast, before spawning anything)

A bad ref or empty diff should fail here, not inside three parallel sessions. Run these read-only checks in the repo:

1. Resolve the base and commit to full hashes: `git rev-parse --verify <base>^{commit}` and `git rev-parse --verify <commit>^{commit}`. Use the hashes from then on, never moving branch names.
2. Require a non-empty three-dot diff: `git diff <base>...<commit> --stat` (compares against the merge base). Capture that output plus `git log <base>..<commit> --oneline` once and paste both into every session prompt.
3. Require a clean, committed tree: `git status --porcelain` must be empty. Uncommitted changes waste an entire agent run. Don't auto-commit or discard anything; stop and let the owner resolve it.

## Folder Structure

Projects that run gate audits keep them under `.apm/gate-audits/` (or your preferred audit folder) in the repo:

```
.apm/gate-audits/
├── GATE-{N}-SESSION-1-SPEC-COMPLIANCE.md
├── GATE-{N}-SESSION-2-BUG-HUNTING.md
├── GATE-{N}-SESSION-3-ADVERSARIAL.md
└── DEVIATION-INVENTORY.md
```

Raw reports go to `tmp/gate-{N}-session-{1a,1b,2a,2b,...}-report.md`. Consolidated findings go to `tmp/gate-{N}-consolidated-findings.md`. Look at existing artifacts before writing; never overwrite another gate's record. Every doc and report states the full pinned hash.

## Scaling Rules

Real codebases overflow one agent's context. Split by **concern area**, not file count:

1. **Split by domain.** Each sub-agent owns one functional area (for example auth and access control, a state machine, UI flows, serverless functions). Two sub-agents per session works well.
2. **Context packs.** For large codebases, pre-extract a scoped bundle per domain: strip comments, collapse imports, keep only relevant functions. Keep a file and line mapping back to the pinned source; the pack is a convenience, not the authority.
3. **Incremental audits after the first full pass.** Later gates audit only changed files plus their direct dependencies. Don't re-audit stable code.
4. **Regression tests replace re-auditing.** Once a bug is fixed, write a test that encodes it. Future PRs run the suite, so audits can focus on what tests can't catch.

## Code-Smell Baseline (Session 2 supplement)

On top of the bug lens, Session 2 sub-agents carry a fixed baseline of Fowler code smells (*Refactoring*, chapter 3). Paste the full list into every Session 2 prompt; the sub-agent has no other access to it.

**Binding rules:**
- **The repo overrides.** A documented repo standard wins. Where the repo endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Label each smell "possible X," never a hard violation.
- **Skip anything tooling already enforces.**

**Baseline** (what it is → fix):
- **Mysterious Name** → rename; if no honest name exists, the design is murky
- **Duplicated Code** → extract the shared shape
- **Feature Envy** → move the method onto the data it envies
- **Data Clumps** → bundle recurring fields into a type
- **Primitive Obsession** → give the domain concept its own type
- **Repeated Switches** → polymorphism or one shared map
- **Shotgun Surgery** → gather scattered edits into one module
- **Divergent Change** → split so each module changes for one reason
- **Speculative Generality** → delete it; inline until a real need appears
- **Message Chains** → hide the walk behind one method
- **Middle Man** → cut the delegator
- **Refused Bequest** → composition over inheritance

## Rules

- **No pre-approved deferrals.** Reviewers find gaps on their own; humans reconcile afterward. False positives beat rubber stamps.
- **Read and report only.** Reviewers have no authority to edit, fix, merge, or release.
- **Pin the commit.** Every doc and report states the exact hash. No moving targets.
- **Severity taxonomy:** 🔴 Critical (fix before merge), 🟡 Should Fix (high value), 🟠 Minor (fix or defer with a reason), ⚪ Defensive Gap (no bug today, breaks under stress).
- **The consolidated findings doc is the handoff.** One file, organized by severity, with file paths and line numbers.
- **Cap each sub-agent report at about 400 words** of findings (quotes and line refs count; preamble doesn't). This forces ranking inside each report and keeps consolidation readable.
- **Never rerank across lenses.** Every finding keeps its session and lens tag. No lens's findings get dropped or demoted because another lens found "bigger" issues. A change can pass one lens and fail another; keeping them separate stops one axis from masking another.

## Dispatch and Verification

Give each sub-agent a complete, self-contained task: its lens and concern area, the repo, resolved hashes, spec and repo rules, the captured diff and log, all binding rules, its output path, and the report cap. Session 2 also gets the full smell baseline. A sub-agent has none of your history, so never send just "review this." Don't seed one lens with another's findings. Each reviewer writes its own report file; only the coordinator writes the consolidation.

Run independent lenses and concerns concurrently. Wait for every reviewer before consolidating or letting fixes ship. A timed-out, failed, or incomplete reviewer means the audit isn't clean. Record reviewer IDs, the models actually used, completion status, and report paths. Keep every finding's original severity and lens; overlapping findings can be cross-linked but never merged away.

## Lessons Learned

- Commit before auditing. Uncommitted changes waste an agent run.
- A mid-tier model handles spec compliance (mechanical comparison) fine. The strongest model earns its cost on bug hunting and adversarial work.
- Session 1 may need splitting (1A + 1B) when the spec is large. Session 2 almost always needs splitting.
- The state-machine gap table from Session 3 is often the highest-value artifact. List every state × event pair with expected vs actual behavior.

**Done means:** clean-tree and non-empty-diff evidence, the same pinned hash in every report, every session and concern area complete, full taxonomy and lens tags retained, state-machine coverage where it applies, and one consolidated handoff.

## Credits

The code-smell binding rules (repo overrides, "possible X" judgement labels, skip tooling-enforced smells) are adapted from the `code-review` skill in [mattpocock/skills](https://github.com/mattpocock/skills) (MIT License, Copyright (c) 2026 Matt Pocock). The smell catalog itself comes from Martin Fowler's *Refactoring* (2nd ed.), summarized here in our own words.
