# PRD Template for Alpha Decay Foundry

**Document type**: Reusable template for phase PRDs (v0.2, v0.3, v0.4, etc.)
**Audience**: Jacopo Dalmasso and any AI agent drafting future PRDs
**Last updated**: April 28, 2026

---

## How to use this template

This template encodes the structure that worked for the v0.1 PRD. Future phase PRDs (v0.2 onward) should follow the same skeleton, adjusted for the phase's specific scope.

The goals of every PRD in this project are:

1. **Self-contained**: an agent should be able to execute the phase from this PRD alone, without reading other documents (except the context document).
2. **Unambiguous**: every architectural decision is either made explicitly or marked as an explicit TODO with a default behavior specified.
3. **Bounded**: the "Out of Scope" section is as important as the "In Scope" section. The most common failure mode is scope creep.
4. **Testable**: success is defined by test cases that can be verified, not by qualitative judgment.

A PRD is correctly scoped if you could hand it to a competent AI coding agent (Claude Code, Cursor agent, OpenAI Codex) on a Friday afternoon and have a passing v0.X by the following weekend with at most one or two clarifying questions.

If a PRD requires three rounds of back-and-forth before the agent can start, the PRD is under-specified.

---

## Required sections

Every phase PRD has these sections, in this order:

### 0. Reading instructions for the executing agent

What to do when ambiguity arises. Default: simpler implementation, TODO comment, continue. Never block on questions.

Should also state: which documents are in scope (context document, prior phase PRDs), which are not, and how to handle conflicts (context document wins).

### 1. Goal and success criteria

**Goal statement**: 1-3 sentences describing what the phase delivers.

**Success criteria**: a numbered list of binary-checkable conditions. Each item must be verifiable without judgment. Bad: "the framework is robust and well-designed." Good: "running `pytest` produces zero failures and ≥85% line coverage."

**Explicit non-goals**: 5-15 items the agent might be tempted to implement but should not. This is the most important sub-section.

### 2. Configuration and optionality

How the phase integrates with the framework's existing optionality system. Every realism feature added in this phase must:

- Default to off / minimum friction
- Be opt-in via the `Configuration` object or constructor parameter
- Have its protocol defined even if not fully implemented

If the phase doesn't add any new optional features, this section can be brief but should not be omitted (it forces the question).

### 3. Repository setup

Changes to:
- Repository structure (new files/directories)
- `pyproject.toml` (new dependencies, version bump)
- CI configuration if needed

For phases after v0.1, this is usually short — the structure is already in place. Just diffs.

### 4. Core protocols

Full type signatures for any new protocols introduced in this phase, plus any modifications to existing protocols.

Format for each protocol:

```python
@runtime_checkable
class NewProtocol(Protocol):
    """One-paragraph description.
    
    Conventions and contract details here.
    """
    name: str
    
    def method(self, ...) -> ReturnType:
        """Method docstring with semantics."""
        ...
```

If the protocol has multiple implementations expected in the same phase, list them with brief acceptance criteria each.

### 5-N. Implementation modules

Per-module sections, in dependency order. For each module:

- **Path**: `src/alpha_decay_foundry/path/to/module.py`
- **Purpose**: one paragraph
- **API**: full type signatures of public classes and functions
- **Implementation notes**: anything non-obvious about how to implement
- **Acceptance criteria**: 2-5 checkable items specific to this module
- **Tests required**: list of test files / test cases

The module ordering should follow strict dependency order — a module's PRD section should appear after all its dependencies. This means an agent reading top-to-bottom can implement in order without forward references.

### Testing section

Two parts:

**Unit tests**: per-module tests are listed in each module's PRD section. This section just specifies the testing infrastructure (fixtures, mocks, conventions).

**Integration test**: the phase's defining end-to-end test. For v0.1 this was the Fama-French replication. For v0.2 it might be the Frazzini-Pedersen BAB replication run through both vectorbt and zipline-reloaded with results within tolerance.

The integration test is what turns success criteria into pass/fail.

### Code conventions

A reference list. Most should already be established by v0.1's PRD; this section captures any new conventions introduced (e.g., "v0.3 introduces async data loading; use `asyncio.to_thread` for blocking I/O").

### Definition of done

A literal checkbox list. The agent works through it; when all boxes are checked, the phase ships. No subjective judgment.

### Out of scope

Comprehensive list. Anything tempting but explicitly not for this phase. The longer this list, the better the PRD.

### TODOs and ambiguity protocol

Pattern:

```python
# TODO(vX.Y-clarify): [question]
# Provisional choice: [implementation]
# Alternative: [other option]
```

Surfaced via `grep -rn "TODO(vX.Y" src/` at end of phase. Jacopo reviews before tagging.

### References

Links to:
- The context document
- The previous phase's PRD
- Any papers being replicated in this phase
- Any external library documentation that's load-bearing

---

## Section sizing guidance

A well-scoped phase PRD is 4,000–7,000 words. Distribution roughly:

| Section | Target words |
|---|---|
| Reading instructions | 100-200 |
| Goal and success criteria | 300-500 |
| Configuration and optionality | 200-500 |
| Repository setup | 200-400 |
| Core protocols | 800-1500 |
| Implementation modules | 1500-3000 |
| Testing | 400-800 |
| Code conventions | 100-300 (if new conventions) |
| Definition of done | 100-200 |
| Out of scope | 200-400 |
| TODOs / references | 100-300 |

A PRD under 3,000 words is probably under-specified. A PRD over 10,000 words is probably trying to do too much in one phase — split into v0.X.1 and v0.X.2.

---

## Patterns that work

**Type signatures over prose.** Showing `def target_weights(self, data: DataProvider, ...) -> TargetWeights` is denser and less ambiguous than describing what the method does in English.

**Acceptance criteria as code.** "Tests verify that weights sum to gross_target ± 0.001" is better than "weights are correctly summed."

**Explicit defaults for optional parameters.** `lifecycle: StrategyLifecycle | None = None` with a docstring saying "None = pure research, no enforcement" leaves no ambiguity.

**Hooks for future versions.** Define protocols and parameters now even if they're not implemented. v0.1's `Configuration.realistic_backtest()` raises `NotImplementedError("Available in v0.2")` rather than not existing — this means v0.2 can populate it without breaking the API.

**The "out of scope" list is the same length as the "in scope" list.** This is roughly true for well-scoped phases. If "out of scope" is much shorter, scope is creeping.

**Integration test as success definition.** Every phase has one specific, end-to-end runnable script that defines success. For v0.1 it was the FF5 replication. For v0.2 it's BAB through two engines. Define this script first, write the PRD around making it pass.

**Replications, not original research.** Each phase delivers a replicated paper, not new research. This forces the framework to be tested against published values rather than judged by aesthetics.

---

## Anti-patterns to avoid

**"And also..." scope creep.** "v0.2 implements zipline-reloaded *and also* introduces options support" — split into separate phases. Every "and also" is a red flag.

**Vague acceptance criteria.** "The framework is performant enough" → unverifiable. "Backtests on the FF5 data complete in under 30 seconds on M1 Mac" → verifiable.

**Forward references without forward definitions.** If module A depends on module B's protocol, B's PRD section comes first. Don't say "use the `RiskOverlay` protocol from later in this PRD" — define it in the right place.

**Configuration via files.** Code-based configuration. No YAML, no TOML except `pyproject.toml`. The framework is a Python library, not a config-driven application. (The exception: secrets and credentials in `.env` files, encrypted, not in the public repo.)

**Premature optimization.** "Use Polars throughout for performance." Use pandas. Switch specific hot paths to Polars when they're measurably slow.

**Premature abstraction.** "All adapters should be plugin-loadable via entry points." True eventually. Wait until you have three adapters of the same type, then abstract.

**TODO without provisional implementation.** A `# TODO(v0.X-clarify): not sure how to handle X` with no implementation following is a blocker. The pattern is: provisional choice + TODO + alternative. The agent never blocks.

**Tests written after implementation.** Tests are part of the PRD's definition of done. Specify test files and test cases in each module section, not as an afterthought.

---

## Drafting workflow

When drafting a new phase PRD:

1. **Re-read the context document** to ground in current project state.
2. **Identify the integration test** (which paper is replicated, what's the end-to-end script). Write it first, in pseudocode.
3. **List dependencies** for that integration test — what modules need to exist?
4. **Write the goal + success criteria** that map to the integration test passing.
5. **Identify what's tempting but out of scope.** This list goes in Section 1's non-goals AND in the "Out of Scope" section.
6. **Define new protocols.** Just type signatures, no implementation.
7. **Module-by-module specs in dependency order.** Each module gets path, API, implementation notes, acceptance criteria, tests.
8. **Testing strategy.** Unit tests already specified per-module; just integration test details here.
9. **Definition of done as checkbox list.** Reference back to success criteria.
10. **Out of scope list.** Aim for 10-20 items, more is better than fewer.

The whole drafting process should take 4-8 hours of focused work. If it's taking longer, the phase scope is probably too large.

---

## Pre-handoff checklist

Before handing a PRD to an executing agent, verify:

- [ ] Success criteria are all binary-checkable
- [ ] Out of scope list is comprehensive (10+ items)
- [ ] Integration test is specified end-to-end
- [ ] Every protocol mentioned has a full type signature
- [ ] Every module has explicit acceptance criteria
- [ ] Dependency order is correct (no forward references)
- [ ] Configuration / optionality treatment is consistent with project philosophy
- [ ] All references (papers, docs, libraries) have URLs
- [ ] Definition of done is a literal checklist
- [ ] PRD compiles in your head — you could implement it yourself given time

If any item fails, fix the PRD before handoff. A 30-minute pre-handoff fix saves 30 hours of agent confusion and rework.

---

## Sample PRD outline for v0.2 (illustrative only)

To make the template concrete, here's how a v0.2 PRD might begin (this is *not* the actual v0.2 PRD — that's drafted when v0.1 ships):

```
# Alpha Decay Foundry v0.2 — Multi-Engine + Portfolio Layer

Phase: v0.2
Estimated effort: 100-140 engineering hours
Prerequisites: Read context doc + v0.1 PRD; v0.1 must be tagged.

## 1. Goal and success criteria

Goal: Add zipline-reloaded as a second backtest engine. Add the
PortfolioOptimizer and RiskOverlay protocols with reference
implementations. Add slippage/cost/tax models as opt-in features.
Validate engine portability by replicating Frazzini-Pedersen
"Betting Against Beta" through both vectorbt and zipline-reloaded
with results matching within tolerance.

Success criteria:
1. The integration test `examples/replicate_bab.py` passes.
2. Running BAB through both engines produces returns within 10bps
   monthly tracking.
3. The new optional features (costs, slippage, taxes) integrate
   cleanly with v0.1 strategies — no v0.1 code modifications required.
4. ...

Explicit non-goals:
- ML strategies (deferred to v0.3)
- Paper trading (deferred to v0.4)
- Real point-in-time index membership (deferred to v0.3)
- ...

## 2. Configuration and optionality

v0.2 introduces three new optional features:
- TransactionCostModel protocol with ConstantBpsCommission default
- SlippageModel protocol with ConstantBpsSlippage default
- TaxModel protocol with USEquityTaxModel default

All default to None in Configuration; opt-in via
Configuration.realistic_backtest() factory.

[... and so on through the rest of the template ...]
```

The point is that the structure is identical to v0.1. Only the content changes.

---

## Maintaining this template

This template is a living document. After each phase ships, review the PRD-as-written against this template:

- What worked? Add to "patterns that work."
- What caused agent confusion? Add to "anti-patterns to avoid."
- What was missing from the structure? Add a new required section.
- What was redundant? Remove.

Aim to update this template after every phase. Two iterations and it should be stable.

---

*End of PRD template. The first phase PRD using this template was v0.1 (`alpha-decay-foundry-v0.1-prd.md`). Future PRDs follow this same structure with phase-appropriate content.*
