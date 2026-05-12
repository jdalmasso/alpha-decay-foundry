# Alpha Decay Foundry — Project Context & Roadmap

**Status:** Living document. Last updated April 28, 2026.
**Intended audience:** Jacopo Dalmasso and any human or AI agent working on the project.
**Purpose:** Single source of truth for project goals, decisions, architecture, and roadmap. Read this before touching any code.

---

## 1. What this is

Alpha Decay Foundry is an open-source Python framework for systematic equity research, backtesting, and live trading. It is the public infrastructure component of a larger project that also includes a private signal research repository and (separately) two Substack publications: one for quant research, one for AI economics commentary.

The two repositories work together:

- **`alpha-decay-foundry`** (public): the framework. Protocols, engine adapters, paper-trading bridge, performance analytics, eventually a dashboard. Distributed as a `pip install`able Python package under Apache 2.0 + Commons Clause. Lives at `github.com/jdalmasso/alpha-decay-foundry`.
- **`alpha-decay-research`** (private): proprietary signal research, live execution glue, broker credentials, position state, current production strategies. Depends on the foundry as a library. Lives at `github.com/jdalmasso/alpha-decay-research`. Operationally inactive until v0.4.

Defensive org `alphadecaylabs` is parked but unused. Substack URLs `alphadecaynotes` (quant) and `computeandcapital` (AI economics) are reserved but not yet active.

## 2. Why this exists

Three converging purposes:

**Personal trading and income.** Deploy personal capital systematically across multiple strategies, eventually publish strategies on platforms like Composer or Collective2, treat this as a serious side venture.

**Academic positioning.** Open-source quantitative research with public replications strengthens PhD and EMBA admissions narratives.

**Career optionality.** The framework + trading + writing combination is rare. Positions the author as a credible practitioner-researcher whether the next move is academic, fund-side, or another startup.

The framework alone is not the moat. The combination is.

## 3. The constraints we're designing around

Time budget: roughly four days per week across this project, math/econ refresher, working paper for PhD applications, and existing advisory commitments. The working paper takes priority when time gets squeezed.

Capital trajectory: $50-100k starting, scaling to $250-500k over 12-18 months.

Domain experience: deep quant background, strong Python and ML, not a software engineer by training. Framework should be production-quality but not over-engineered. Use established libraries where they exist; build only at the abstraction layer.

## 4. Intellectual anchor: Grinold and Kahn

*Active Portfolio Management* (Grinold & Kahn, 2nd ed., 2000) is the intellectual backbone. The vocabulary, metrics, and pipeline should reflect Grinold-Kahn explicitly:

- **Information Coefficient (IC)** as primary signal evaluation tool. Correlation between forecasts at time t and realized returns at t+1. Reported alongside Sharpe.
- **Information Ratio (IR)** as primary strategy evaluation tool. Annualized excess return over annualized tracking error.
- **Fundamental Law of Active Management**: IR ≈ IC × √breadth. Decomposed and reported for every strategy.
- **Forecast → portfolio pipeline**: signals produce forecasts; forecasts drive portfolio weights. Framework architecture mirrors this.

Documentation, naming, and analytics reflect Grinold-Kahn throughout.

## 5. Key decisions made and why

### 5.1 Multi-engine architecture, weight-centric interface

Strategies emit target portfolio weights as a time series. The execution engine is a downstream consumer. Same Strategy code runs across vectorbt (research), zipline-reloaded (factor research), paper trading (Alpaca), eventually live (LEAN).

### 5.2 Three-period validation lifecycle

Every strategy progresses through: in-sample backtest → out-of-sample paper trading (min 6 months) → live. Enforced at the framework level. Optional, with `research_only` factory available for pure research.

### 5.3 Look-ahead enforcement via AsOfDataProvider

Backtesting wraps data access through an as-of provider that refuses requests beyond the simulated current time. The strategy literally cannot see future data.

### 5.4 Open-source framework, paid-via-other-channels monetization

Framework is open source (Apache 2.0 + Commons Clause). Monetization through trading P&L, paid Substack, eventually Composer/Collective2 subscriptions. No "Pro" framework version is built.

### 5.5 Equities + ETFs only through v1.0

Options, futures, crypto, prediction markets all post-v1.0.

### 5.6 Public framework as installable package

`pip install alpha-decay-foundry` from day one. Extension points use Python's entry-point system.

### 5.7 Qlib as upstream ML adapter, not foundation

Qlib used as a `Strategy` implementation via an adapter, introduced in v0.3.

### 5.8 Cost trajectory tied to phase, not aspirations

Free data through v0.1. Norgate joins in v0.1.2 ($45-65/mo). Sharadar joins in v0.2 ($150/mo). Vectorbt PRO when sweeps justify it (~$20/mo). LLM API costs scaled to specific replication scope.

Year-1 total: roughly $2,000-4,000 across data, infrastructure, LLM APIs.

### 5.9 Optionality with sensible defaults

Every realism feature (costs, slippage, taxes, lifecycle enforcement) defaults to off. Opt-in via `Configuration` object. Lifecycle defaults to `research_only`; `standard` mode required for live deployment.

### 5.10 Issue-PR-audit workflow

Every change happens through: GitHub issue (2-8 hours of scope) → branch → PR → automated audit by separate reviewing agent → merge. No PR exceeds 500 lines. Audit findings either auto-resolve or escalate to Jacopo for ambiguous cases.

### 5.11 Daily bar frequency from v0.1

Daily-bar discipline from the start. Monthly aggregation only for cross-sectional rebalancing where appropriate. This forces correct handling of trading calendars, holidays, and corporate action dates from day one.

## 6. Architecture in one page

Seven core protocols:

1. **`Universe`** — what's tradable when (handles delistings, IPOs, index changes)
2. **`DataProvider`** — point-in-time data access, wrapped by `AsOfDataProvider` during simulation
3. **`Signal`** — transformation from data to numeric score per asset per time
4. **`Strategy`** — composition of signals into target portfolio weights
5. **`PortfolioOptimizer`** — combines multiple strategies into one book
6. **`RiskOverlay`** — applies constraints
7. **`ExecutionEngine`** — takes target weights, runs in backtest / paper / live mode

State flows through `PortfolioState`. The three-period `StrategyLifecycle` is metadata attached to every strategy.

Storage: DuckDB + Parquet files in `~/.alpha_decay_foundry/cache/` for all data. Cached snapshots are versioned by download date for reproducibility.

## 7. Phased roadmap

### v0.1 — Free-data validation harness (months 1-2)

**Goal:** Prove the architecture works end-to-end using only free data (OSAP + Ken French). Replicate Fama-French 5-factor with daily-bar discipline. Validate against both OSAP and French published returns within tolerance.

**Why no paid data yet:** v0.1's purpose is validating that the abstractions are correct, not producing novel research. Free data is sufficient. Paid data joins in v0.1.2.

**In scope:** Core protocols, AsOfDataProvider, DuckDB+Parquet caching, OSAP and French data providers, OSAP-lookup-based signals, `LongShortQuintile` strategy, vectorbt engine, full Grinold-Kahn analytics suite, daily bars, monthly rebalancing, trading calendar.

**Decision gate at end:** Are abstractions clean enough that paid data plugs in via a new adapter, without protocol changes? If yes, proceed to v0.1.2.

### v0.1.2 — Paid data integration (month 3)

**Goal:** Prove the `DataProvider` abstraction by integrating Norgate. Validate framework produces results consistent with v0.1's OSAP-based replication.

**In scope:** `NorgateDataProvider` (price data, point-in-time index membership, corporate actions, survivorship-free universes), `SP500Universe` and `Russell3000Universe` with real point-in-time membership, validation that FF5 replication matches across data sources.

**What needs to be proven:** No `DataProvider` protocol changes needed. Norgate plugs in cleanly. Corporate action handling produces results within tolerance.

**Cost trigger:** Norgate subscription begins, ~$45-65/mo.

### v0.2 — Multi-engine + portfolio + raw fundamentals (months 4-5)

**Goal:** Replicate Frazzini-Pedersen "Betting Against Beta" through both vectorbt and zipline-reloaded. Add raw fundamentals via Sharadar. Add portfolio optimizer, risk overlays, cost/slippage/tax models.

**In scope:** zipline-reloaded engine, `SharadarDataProvider` for fundamentals (computing signals from raw inputs, not OSAP lookups), `PortfolioOptimizer` protocol, `RiskOverlay` protocol, slippage/cost/tax models.

**Cost trigger:** Sharadar subscription begins, +$150/mo.

**Replications:** BAB through both engines. Asness-Frazzini-Pedersen QMJ.

### v0.3 — ML and alt-data (months 6-7)

**Goal:** Replicate Cohen-Malloy-Nguyen "Lazy Prices" using SEC EDGAR. Begin Lopez-Lira & Tang LLM news replication. Implement Qlib adapter.

**In scope:** `EDGARProvider`, `NewsProvider`, `LLMSignal` infrastructure, `QlibStrategy` adapter, walk-forward utilities.

**Cost:** Add LLM API costs (~$50-300 one-time, ~$30/mo ongoing).

### v0.4 — Paper trading bridge (months 8-9)

**Goal:** First strategy live in paper trading via Alpaca. Streamlit dashboard.

**In scope:** `PaperTradingEngine` against Alpaca paper API, live `PortfolioState` tracking, monitoring, dashboard.

### v1.0 — Live trading (months 10+)

**Goal:** First live-traded strategy on personal capital. LEAN integration. Public release.

### v1.1+ — Optionality

- Composer/Collective2 strategy publishing
- Options strategies
- Prediction markets module

## 8. Replication slate

| Paper | Phase | What it proves about the framework |
|---|---|---|
| Fama-French 5-factor (2015) | v0.1 / v0.1.2 | End-to-end pipeline works; abstractions support multiple data sources |
| Frazzini-Pedersen BAB (2014) | v0.2 | Engine portability; risk overlay handles leverage |
| Asness Frazzini Pedersen QMJ (2019) | v0.2 | Multi-component factor construction |
| Jensen-Kelly-Pedersen replication crisis (2023) | v0.2-v0.3 | International data + Bayesian factor synthesis |
| Cohen-Malloy-Nguyen Lazy Prices (2020) | v0.3 | Text data, EDGAR pipeline |
| Lopez-Lira & Tang LLM news (2023, rev 2025) | v0.3 | LLM signal infrastructure |
| Gu-Kelly-Xiu ML asset pricing (2020) | v0.3-v0.4 | Qlib adapter, large-scale ML |
| Kelly et al. AI Asset Pricing Models (2025) | v0.4+ | Frontier transformer architecture |

## 9. Decision gates between phases

- **End of v0.1**: are abstractions clean enough to plug in paid data without protocol changes?
- **End of v0.1.2**: are corporate action and survivorship handling correct? Does Norgate-based replication match OSAP-based within tolerance?
- **End of v0.2**: is the framework portable enough for complex strategies?
- **End of v0.3**: is alt-data infrastructure stable enough to bridge to paper trading?
- **End of v0.4**: per-strategy go-live decision based on defined criteria

Each gate has explicit criteria. Default answer is "delay" rather than "force forward."

## 10. Out of scope

**Permanently:**
- High-frequency trading
- Market making
- Real-time order book or tick-level execution
- Building a custom backtesting engine from scratch

**Out of scope for v0.1-v1.0:**
- Asset classes other than US equities and ETFs
- Multi-currency support
- Distributed compute
- Custom database backend (DuckDB + Parquet is sufficient)
- Pro version of framework
- UI beyond v0.4 Streamlit dashboard

## 11. Tech stack reference

**Language**: Python 3.11+ (3.13 supported when libraries catch up)
**Package management**: uv preferred
**Type checking**: mypy in strict mode for core protocols
**Testing**: pytest with hypothesis
**Storage**: DuckDB + Parquet
**CI**: GitHub Actions
**Linting**: ruff

**v0.1 core dependencies:**
- pandas, numpy, polars (where speed matters)
- duckdb, pyarrow (storage)
- pydantic v2
- vectorbt
- exchange-calendars (trading day handling)
- scipy, statsmodels (analytics, Newey-West)
- requests (data downloads)

**Optional dependencies by phase:**
- v0.1.2: norgatedata
- v0.2: zipline-reloaded, nasdaqdatalink (for Sharadar)
- v0.3: qlib, alpaca-py, openai, anthropic, sec-edgar-downloader
- v0.4: streamlit + plotly

## 12. References

**Foundational papers:**
- Fama & French (2015) — JFE 116(1)
- Frazzini & Pedersen (2014) — JFE 111(1)
- Cohen, Malloy & Nguyen (2020) — JF 75(3)
- Jensen, Kelly & Pedersen (2023) — JF 78(5)
- Kelly, Kuznetsov, Malamud & Xu (2025) — NBER WP 33351

**Backbone:**
- Grinold & Kahn, *Active Portfolio Management* (2nd ed., 2000)

**Tooling:**
- Stefan Jansen, *Machine Learning for Algorithmic Trading*
- vectorbt: vectorbt.dev
- Tidy Finance: tidy-finance.org

**Data:**
- Open Source Asset Pricing: openassetpricing.com
- JKP factors: jkpfactors.com
- Ken French data library: mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- Norgate Data: norgatedata.com (v0.1.2)
- Sharadar SF1: data.nasdaq.com/databases/SFB (v0.2)

---

*This document is the project's anchor. If something is decided contrary to it, this doc is updated. If something is in this doc but no longer correct, this doc is updated.*
