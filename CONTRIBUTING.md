# Contributing to Alpha Decay Foundry

## Workflow: Issue → Branch → PR → Audit → Merge

Every change goes through this loop. No exceptions.

### 1. Create an issue first

Title format: `[v0.X] <module>: <specific change>`. Body must include:

- **Scope**: what changes and what doesn't
- **Acceptance criteria**: binary-checkable conditions
- **Effort estimate**: 2-8 hours
- **PRD reference**: which section of the current PRD this addresses

Issues larger than 8 hours must be split.

### 2. Branch and implement

Branch name: `v0.X/<issue-number>-<short-description>` (e.g. `v0.1/3-core-types`).

Implement against the acceptance criteria. Write tests as you go. Run locally before pushing:

- `uv run ruff check src tests`
- `uv run mypy src/alpha_decay_foundry --strict`
- `uv run pytest`

All three must pass before opening a PR.

### 3. Open a PR

Link to the issue with `Closes #N`. Fill out the PR template:

- Summary of change (1-3 sentences)
- Acceptance criteria with checkmarks
- Manual testing performed
- Out-of-scope items deliberately left for future issues
- Audit notes (anything the reviewing agent should know)

PRs over 500 lines must be split.

### 4. Audit

A separate Claude Code session reviews the PR using `docs/audit-prompt.md`. Verdicts:

- **APPROVE**: PR can merge
- **BLOCK WITH CHANGES**: cycle back, address findings, request re-review
- **ESCALATE**: ambiguous question forwarded to Jacopo

### 5. Merge

Only when audit returns APPROVE and CI is green. Squash-merge.

## Code conventions

- `from __future__ import annotations` at top of every file
- Type hints required everywhere; `mypy --strict` must pass
- Google-style docstrings on every public class and function
- Use the framework's exception hierarchy from `core/exceptions.py`
- Use `logging.getLogger(__name__)` per module; no print statements
- snake_case for functions and variables, PascalCase for classes, leading underscore for private
- Pandas: prefer explicit `.loc[]` over chained indexing
- Datetime: always `pd.Timestamp` with UTC timezone; never naive `datetime.datetime` in public APIs
- Analytics functions reference Grinold-Kahn chapter where relevant in docstrings

## TODO discipline

Any TODO must follow this format:

- `TODO(v0.X-clarify): <brief question>`
- Include a provisional choice and an alternative in a comment immediately below

Loose TODOs without context are not acceptable.
