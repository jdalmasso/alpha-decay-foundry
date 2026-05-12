# Alpha Decay Foundry

Open-source Python framework for systematic equity research, backtesting, and live trading.

> [!NOTE]
> v0.1 is in active development. The framework is not yet production-ready and the API will change. Star the repo to follow along.

## What this is

Alpha Decay Foundry is a framework for building, backtesting, and eventually deploying systematic equity strategies. It's designed around three principles:

**Engine-portable strategies.** A `Strategy` emits target portfolio weights as a time series. Backtest engines (vectorbt, zipline-reloaded), paper trading engines, and live engines are downstream consumers. Strategy code never changes when the engine changes.

**Look-ahead bias by construction, not discipline.** Every backtest wraps data access through an `AsOfDataProvider` that refuses to return data beyond the simulated current time. Strategies cannot peek into the future, even if their authors try.

**Three-period validation lifecycle.** Strategies progress through in-sample backtest → minimum 6 months paper trading → live deployment. Live engines refuse to deploy strategies that haven't completed the paper trading phase.

The intellectual backbone is Grinold and Kahn's *Active Portfolio Management*. Information Coefficient, Information Ratio, and the Fundamental Law of Active Management are first-class concepts throughout.

## Roadmap

| Phase | Status | Description |
|---|---|---|
| v0.1 | In progress | Free-data validation harness. Fama-French 5-factor replication via OSAP and Ken French data |
| v0.1.2 | Planned | Paid data integration via Norgate. Real point-in-time index membership and survivorship-bias-free universes |
| v0.2 | Planned | zipline-reloaded second engine, Sharadar fundamentals, portfolio optimizer, risk overlays, cost/slippage/tax models |
| v0.3 | Planned | ML strategies via Qlib adapter, alt-data (SEC EDGAR, news), LLM-based signals |
| v0.4 | Planned | Paper trading bridge via Alpaca, Streamlit monitoring dashboard |
| v1.0 | Planned | Live trading via LEAN, public release |

## Installation

Requires Python 3.11 or 3.12. Uses [uv](https://docs.astral.sh/uv/) for package management.

```bash
git clone https://github.com/jdalmasso/alpha-decay-foundry.git
cd alpha-decay-foundry
uv sync --extra dev
```

To run tests, lint, and type-check:

```bash
uv run pytest
uv run ruff check src tests
uv run mypy src/alpha_decay_foundry --strict
```

## Documentation

- **[Project context and roadmap](docs/context.md)** — start here for the full project rationale and architectural decisions
- **[v0.1 PRD](docs/v0.1-prd.md)** — current development scope and module specifications
- **[Audit prompt](docs/audit-prompt.md)** — the standing instructions for the reviewing agent
- **[PRD template](docs/prd-template.md)** — structure for future phase PRDs
- **[Contributing](CONTRIBUTING.md)** — issue → PR → audit → merge workflow

## Architecture

Seven core protocols compose the framework:

1. **`Universe`** — defines what assets are tradable at each point in time
2. **`DataProvider`** — point-in-time data access, wrapped by `AsOfDataProvider` during simulation
3. **`Signal`** — transformation from data to numeric forecasts per asset per time
4. **`Strategy`** — composition of signals into target portfolio weights
5. **`PortfolioOptimizer`** — combines multiple strategies into one book (v0.2+)
6. **`RiskOverlay`** — applies position and exposure constraints (v0.2+)
7. **`ExecutionEngine`** — runs target weights in backtest, paper, or live mode

State flows through `PortfolioState`. The three-period `StrategyLifecycle` is metadata attached to every strategy that goes beyond research into paper or live execution.

Storage uses DuckDB and Parquet files. Cache is reproducibility-first: every downloaded dataset is versioned by download date.

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).

The Commons Clause restricts selling the framework as a primary product. Individual and organizational use is permitted. This is the same license vectorbt uses.

## Author

Jacopo Dalmasso. Mexico City and San Francisco.

Background: previously quantitative researcher at BlackRock and Point72, currently COO at Nuraxi.

Companion publication (forthcoming): notes on systematic investing, factor research, and the practitioner-research process.

## Acknowledgments

This project draws methodology and data from work by:

- **Richard Grinold and Ronald Kahn** — *Active Portfolio Management* (2nd ed., 2000)
- **Andrew Chen and Tom Zimmermann** — [Open Source Asset Pricing](https://www.openassetpricing.com/) project, providing replicated factor returns and characteristics
- **Eugene Fama and Kenneth French** — [Ken French's data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), the foundational source for factor returns
- **Stefan Jansen** — *Machine Learning for Algorithmic Trading* and the maintained zipline-reloaded fork
- **Olivier Polverini and the vectorbt team** — vectorbt, the v0.1 reference backtest engine
