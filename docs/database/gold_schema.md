# Gold Layer - Technical Indicators, Trading Features, Signals and Feature Tables

## Purpose

The Gold layer computes and persists technical indicators, trading features, signals, and final consolidated datasets (Feature Tables) on top of the Silver aggregated candles.

Gold is optimized for consumption by the algorithmic trading bot, backtesting engines, machine learning models, and future dashboards / analysis. The final output is the **Feature Tables** layer.

## Architecture

The full Gold architecture follows the medallion refinement:

```
Bronze
  ↓
Silver (market_candles_*)
  ↓
Gold Indicators (market_indicators_*)
  ↓
Gold Features (market_features_*)
  ↓
Gold Signals (market_signals_*)
  ↓
Gold Feature Tables (market_dataset_*)
```

Gold **Indicators** read exclusively from Silver.

Gold **Features** consume **exclusively** existing Gold Indicator tables (joined with Silver Candles only when necessary for price-action calculations). Features never recalculate indicators, never read from Bronze/Staging, and never duplicate OHLCV or indicator values.

Gold **Signals** consume **exclusively** Gold Features + Gold Indicators. Signals are generic boolean/integer flags (not final trade decisions). They provide structured context for the trading bot or ML models. Signals never recalculate anything from lower layers.

Gold **Feature Tables** are the final consolidated layer. They consume exclusively the three previous Gold layers (Indicators + Features + Signals) and produce clean, ready-to-consume datasets containing only keys + features + signals. No recalculation occurs at this layer.

## Models

### Indicators
- market_indicators_5m
- market_indicators_15m
- market_indicators_30m
- market_indicators_1h
- market_indicators_1d

Materialization: incremental + MERGE

Primary key: (exchange, symbol, open_time)

### Incremental window strategy

Indicator models identify rows that are not yet materialized by the natural key
`(exchange, symbol, open_time)`. The incremental cutoff is evaluated per
`exchange` and `symbol`; a global `MAX(open_time)` is not used. Missing rows
with an older timestamp are also detected so a delayed symbol is not silently
skipped.

For every affected symbol, the complete available Silver candle history is
loaded into the window-calculation CTEs before the final projection is filtered
to rows that must be materialized. This preserves the historical context used
by the cumulative MACD signal and the rolling 20-period Bollinger standard
deviation. The indicator formulas themselves are unchanged. Rows in the
warm-up portion of a series may legitimately remain NULL when their window
does not yet contain enough observations.

### Features
- trend_features (ephemeral, reusable impl)
- momentum_features (ephemeral, reusable impl)
- volatility_features (ephemeral, reusable impl)
- price_action_features (ephemeral, reusable impl)
- market_features_5m
- market_features_15m
- market_features_30m
- market_features_1h
- market_features_1d

The `market_features_*` models are the persisted outputs (incremental MERGE, unique_key = exchange, symbol, open_time).

The category `*_features` (ephemeral) provide reusable grouped implementations.

Materialization (features): market_features_* = incremental + MERGE; categories = ephemeral

Primary key: (exchange, symbol, open_time)

### Signals
- market_signals_5m
- market_signals_15m
- market_signals_30m
- market_signals_1h
- market_signals_1d

Materialization: incremental + MERGE

Primary key: (exchange, symbol, open_time)

No ephemeral category models are persisted for signals (logic lives purely in macros + orchestration models).

### Feature Tables
- market_dataset_5m
- market_dataset_15m
- market_dataset_30m
- market_dataset_1h
- market_dataset_1d

These are the final persisted datasets.

Materialization: incremental + MERGE

Primary key: (exchange, symbol, open_time)

Each row = exactly one candle timeframe bar.

Contain: keys + **all** Features + **all** Signals.

Do not contain any OHLC/OHLCV or raw indicator values.

### BI consumption view

- `market_dataset_bi` (`dbt/models/gold/bi/market_dataset_bi.sql`)

Materialization: **view** (not a table, not incremental)

Purpose:

- Single read model for **Business Intelligence** (primarily **Power BI**).
- Unifies all Gold Feature Tables with `UNION ALL`.
- Adds one column only: **`timeframe`** (`5m`, `15m`, `30m`, `1h`, `1d`).

Logical grain for BI:

```
(exchange, symbol, open_time, timeframe)
```

Important:

- Does **not** replace `market_dataset_*`.
- Adapts numeric feature columns to PostgreSQL `double precision` for BI
  consumers such as Power BI. The original numeric types and precision of the
  canonical Gold tables remain unchanged; the view does not round values or
  replace legitimate `NULL`s.
- Trading Bot, backtesting and future ML consumers keep reading
  `market_dataset_5m` … `market_dataset_1d` directly.
- No recalculation: pure projection over existing Feature Tables via `ref()`.

### OHLCV BI consumption view

- `market_candles_bi` (`dbt/models/gold/bi/market_candles_bi.sql`)

Materialization: **view** (not a table and not incremental)

Purpose:

- Consumption view for **Business Intelligence**, primarily **Power BI**.
- Unifies the five Silver aggregated candle models:
  `market_candles_5m`, `market_candles_15m`, `market_candles_30m`,
  `market_candles_1h` and `market_candles_1d`.
- Adds the `timeframe` label (`5m`, `15m`, `30m`, `1h`, `1d`) so Power BI can
  filter and compare candle resolutions in one model.
- Exposes the existing OHLCV fields and Silver candle attributes for price,
  volume and candlestick visualizations.

The view contains no new calculations and does not recalculate or physically
duplicate candles. It does not replace any Silver model. `market_dataset_bi`
remains the Power BI source for Gold features, signals and KPI datasets; this
view is specifically for OHLCV and candlestick use cases.

Output columns:

```
exchange, symbol, open_time, close_time,
open_price, high_price, low_price, close_price,
volume, quote_asset_volume, number_of_trades,
taker_buy_base_volume, taker_buy_quote_volume, ingested_at,
candle_direction, body_size, upper_wick, lower_wick,
candle_range, typical_price, ohlc_average, timeframe
```

## Indicators Implemented

- EMA (9, 21, 50, 200) - using weighted exponential smoothing (finite history EMA)
- SMA (20, 50, 200)
- RSI (14) - Wilder implementation
- MACD (macd, signal, histogram) - full standard implementation
- ATR (14) - with True Range
- Bollinger Bands (upper, middle, lower)

## Features Implemented

### Trend
- ema9_distance_pct, ema21_distance_pct, ema50_distance_pct, ema200_distance_pct
- ema_alignment (strict ordering EMA9 > EMA21 > EMA50 > EMA200)
- ema_slope_9, ema_slope_21, ema_slope_50
- price_vs_ema50_pct, price_vs_ema200_pct

### Momentum
- rsi_normalized ((RSI-50)/50 → range approx -1..1)
- macd_strength (MACD relative to price)
- macd_histogram_pct
- price_change_5, price_change_10, price_change_20 (pct change over N periods in tf)

### Volatility
- atr_pct (ATR normalized by price)
- rolling_std (20-period rolling std of price, pct)
- bollinger_width
- bollinger_position

### Price Action
- candle_body_ratio, upper_wick_ratio, lower_wick_ratio (normalized by candle range; leverages Silver attributes)
- distance_to_20_high, distance_to_20_low
- distance_to_50_high, distance_to_50_low

## Signals Implemented

All signals are derived **only** from existing Gold Features and Gold Indicators. No recalculation.

### Trend Signals
- ema_bullish_alignment, ema_bearish_alignment
- price_above_ema50, price_above_ema200
- golden_cross, death_cross

### Momentum Signals
- rsi_overbought (rsi_14 >= 70), rsi_oversold (rsi_14 <= 30)
- rsi_recovering
- macd_bullish_cross, macd_bearish_cross
- macd_positive

### Volatility Signals
- high_volatility (atr_pct or bollinger_width thresholds)
- low_volatility
- bollinger_breakout_up (position > 1), bollinger_breakout_down (position < 0)

### Breakout Signals
- new_20_high, new_20_low, new_50_high, new_50_low (based on distance_to_* <= 0.05)
- breakout_confirmation (new high + momentum/alignment confirmation)

## Feature Tables

The Feature Tables (`market_dataset_*`) are the **final output layer** of the Gold medallion.

Purpose:
- Provide a single, clean, denormalized table per timeframe ready for:
  - Algorithmic trading bot (live inference)
  - Backtesting engines
  - Machine Learning feature stores / training datasets
  - Exploratory data analysis
  - Future BI dashboards

Each table contains:
- Natural key (exchange, symbol, open_time)
- Every trading Feature previously computed
- Every Signal previously computed

No raw price data, no indicators, no duplication.

Models are intentionally trivial (pure joins + projection) so that all business logic remains in the lower reusable layers.

## Implementation

Gold **indicator** models act as orchestration layers:
- They read from the corresponding Silver timeframe model.
- They prepare common CTEs (row numbering, True Range, gain/loss for RSI, etc.).
- They call reusable dbt macros for each indicator calculation.

Indicator implementations live in `dbt/macros/gold/indicators/`:
- ema.sql, sma.sql, rsi.sql, atr.sql, bollinger.sql, macd.sql

Gold **feature** models follow the same philosophy:
- `market_features_*` are thin orchestrators: join the corresponding `market_indicators_*` + `market_candles_*` (only for OHLC needed by price action / changes), prepare source, compute category CTEs, join categories for final column union.
- All feature formulas live in single implementation inside `dbt/macros/gold/features/` (trend.sql, momentum.sql, volatility.sql, price_action.sql).
- Category models (`trend_features.sql` etc) under `dbt/models/gold/features/` serve as reusable implementations (ephemeral) and grouping.
- A single implementation per feature. No recalc of indicators. No direct Bronze reads.

Gold **signal** models follow exactly the same layered reusable macro approach:
- `market_signals_*` are thin orchestrators: join the corresponding `market_features_*` + `market_indicators_*`, prepare source with required columns, compute category CTEs using macros, join for final column union.
- All signal logic lives in single implementation inside `dbt/macros/gold/signals/` (trend_signals.sql, momentum_signals.sql, volatility_signals.sql, breakout_signals.sql).
- Signals always use BOOLEAN (or SMALLINT/INTEGER when appropriate). Never store raw values.
- A single implementation per signal. No recalc of features or indicators. No direct access to candles or lower layers.

Gold **feature table** models are the simplest layer:
- `market_dataset_*` are pure consolidation models.
- They perform only joins between the three upstream Gold models for the same timeframe (indicators + features + signals).
- They project exactly the keys + all feature columns + all signal columns.
- Zero calculations, zero CASE statements, zero new logic.
- Their only job is to produce the final clean dataset for consumers.

## Adding New Features in the Future

1. Add a new macro (or extend existing category macro file) in `dbt/macros/gold/features/`.
2. Use the macro inside the appropriate category ephemeral model (`models/gold/features/<category>_features.sql`) as reference.
3. Add the column computation (via macro) inside the 5 `market_features_*` orchestration models (in the proper category CTE).
4. Add column entry + tests in `dbt/models/gold/gold.yml`.
5. Document the new feature in this file under the relevant category.
6. Add small commit, run `dbt compile && dbt run --select gold && dbt test --select gold`.

This guarantees one source of truth and consistency across all timeframes.

## Adding New Signals in the Future

1. Add or extend a macro in `dbt/macros/gold/signals/<category>_signals.sql` (single implementation).
2. Add the signal computation (via macro) inside each of the 5 `market_signals_*` models (in the proper category CTE in the source join).
3. Add column entry (with description and not_null where appropriate) in `dbt/models/gold/gold.yml`.
4. Document under the relevant category in this file.
5. Small commit + full validation: `dbt compile && dbt run --select gold && dbt test --select gold`.

Signals must derive exclusively from already-computed Features and Indicators.

## Adding New Columns to Feature Tables in the Future

Since Feature Tables are pure projections:

1. Add the new column to the appropriate lower layer first:
   - New indicator → indicators macro + model
   - New feature → features macro + category + market_features model
   - New signal → signals macro + market_signals model
2. Add the new column to the corresponding `market_dataset_<tf>.sql` SELECT (from the source CTE that provides it).
3. Add the column (with description and tests) to the model entry in `dbt/models/gold/gold.yml`.
4. Update the Feature Tables section in this document.
5. Run small commit + `dbt compile && dbt run --select gold && dbt test --select gold`.

The Feature Table models should remain trivial. All intelligence stays in Indicators / Features / Signals.

## Incremental Strategy

Similar to Silver and Indicators: reprocessing window (tf-dependent: 30d for 5m ... 400d for 1d) to allow recalculation when new or corrected data arrives.

## Testing

- not_null tests on keys (exchange, symbol, open_time) for all models.
- Basic coverage for feature models, signal models and feature table models in gold.yml.
- Full validation via `dbt test --select gold`.

## Data Flow

```
Bronze (raw klines, prices, snapshots)
  ↓
Silver (normalized + aggregated candles per timeframe)
  ↓
Gold Indicators (market_indicators_*)
  ↓
Gold Features (market_features_*)
  ↓
Gold Signals (market_signals_*)
  ↓
Gold Feature Tables (market_dataset_*)   ← final consumable datasets
```

- Silver aggregated candles → Gold Indicators
- Gold Indicators + Silver candles (only when needed) → Gold Features
- Gold Features + Gold Indicators → Gold Signals
- Gold Indicators + Gold Features + Gold Signals → Gold Feature Tables (only features + signals persisted)

Final consumers (trading bot, backtesting, ML, dashboards) should read primarily from the `market_dataset_*` tables. When raw indicator values are needed, join with the corresponding `market_indicators_*` or `market_features_*`.

No layer ever reads Bronze or Staging directly (except the first Gold layer).
