# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001 | convention | Commit confirmation authority | Final approval is always user before commit | User explicitly requested final commit control | No |
| D002 | M001 | scope | Automation boundary | Auto-apply only low-risk updates (tests/logging/small refactor) | Preserve speed without uncontrolled behavior changes | Yes — if user expands automation scope |
| D003 | M001 | pattern | Session memory inputs | Use commit history + progress.md + .gsd state together | Reduces context loss and wrong next-action selection | Yes — if source reliability changes |
| D004 | M001 | operability | Status visibility | Single-glance state must show active work + blockers + next action | Primary user value is immediate orientation at session start | No |
