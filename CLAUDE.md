# Project: Alpha Decay Foundry

## Read first, every session

Before doing any work, you must have read:

1. `docs/context.md` — strategic context and architectural decisions
2. `docs/v0.1-prd.md` — current development scope and specifications
3. `CONTRIBUTING.md` — the workflow you must follow

If you have not just read all of these in the current session, read them now before proceeding.

## Operating mode

You are working through the v0.1 issue backlog independently. You do not wait for human approval between routine steps. You only stop and ask Jacopo when:

- The PRD genuinely does not cover a situation you've encountered
- A test that should pass is failing in a way you cannot explain after 3 debugging attempts
- You've finished all available work

In every other case, proceed without asking.

## Workflow per issue

For each issue you pick up:

1. Read the issue body completely
2. Read the PRD sections it references
3. Verify no other open PR conflicts with your changes
4. Create the correctly-named branch: `v0.1/<issue-number>-<short-description>`
5. Implement against the acceptance criteria
6. Write tests as you implement (do not save tests for last)
7. Run `uv run ruff check`, `uv run mypy src/alpha_decay_foundry --strict`, and `uv run pytest`
8. Fix any failures (this is not optional)
9. Commit with a message in the format: `<area>: <change> (#<issue-number>)`
10. Push the branch
11. Open a PR using `gh pr create` with a body filled per the template below
12. Stop and report after opening the PR; wait for the audit to be run

Do not start work on a new issue while a previous PR has unaddressed audit feedback.

## Selection of next issue

When picking the next issue, prefer in this order:

1. Issues whose dependencies are merged
2. Issues with smaller estimated effort
3. Issues in `core/` before any other area
4. Issues you have not yet attempted

If no issues are available (all blocked by dependencies or in review), stop and report status.

## After audit feedback

When Jacopo or the audit agent posts a verdict on your PR:

- **APPROVE**: Jacopo will tell you to merge and continue to the next issue
- **BLOCK WITH CHANGES**: address each specific change requested, push new commits, re-request review
- **ESCALATE**: stop work on the issue, post a brief comment summarizing the question on the PR, and move to the next available issue while waiting for Jacopo's decision

## Constraints

- Never modify files in `docs/` unless explicitly asked by Jacopo
- Never exceed 500 lines of changes in a single PR
- Never deviate from the PRD's specified design without first raising the question
- Never disable or weaken tests to make them pass
- Always use the framework's exception hierarchy from `core/exceptions.py`
- All timestamps in public APIs are UTC-aware
- Run `uv run` for all Python invocations (we use uv, not raw python)
- For any TODO, use the format `TODO(v0.1-clarify): <question>` with a provisional choice and an alternative documented in the comment
- Delete `tests/test_placeholder.py` when implementing the first real tests (issue #1)

## PR template

When opening a PR, use this structure in the body:

- A line saying `Closes #N` where N is the issue number
- A Summary section: 1-3 sentences on what changed
- An Acceptance criteria section: each criterion from the issue, with a checked checkbox
- A Manual testing performed section: what you ran locally and what you verified
- An Out of scope section: anything tempting but deferred to future issues
- An Audit notes section: anything the audit agent should specifically know

## When stuck

After 3 failed debugging attempts on the same problem, stop. Add a comment to the PR addressed to Jacopo, summarizing:

- The specific issue you are blocked on
- The approaches you have tried
- The symptoms you are observing
- Your best hypothesis for the root cause

Then move to the next available issue and let Jacopo unblock when he checks in.

## When everything is blocked

If all open issues are either in review or blocked by unmerged dependencies, post a status comment on the most recent open PR summarizing what is complete and what is blocked. Then end your session and wait for Jacopo to restart you after merging.
