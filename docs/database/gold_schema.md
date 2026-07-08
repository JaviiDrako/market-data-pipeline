# Gold Layer - Technical Indicators and Trading Features

## Purpose

The Gold layer computes and persists technical indicators and trading features on top of the Silver aggregated candles.

Gold is optimized for consumption by the algorithmic trading bot and downstream Feature Tables / Signals.

## Architecture

The full Gold architecture follows the medallion refinement:

```
Silver (market_candles_*)
    ↓
Gold Indicators (market_indicators_*)
    ↓
Gold Features (market_features_*)
    ↓
Gold Signals (future)
    ↓
Feature Tables (future)
```

Gold **Indicators** read exclusively from Silver.

Gold **Features** consume **exclusively** existing Gold Indicator tables (joined with Silver Candles only when necessary for price-action calculations). Features never recalculate indicators, never read from Bronze/Staging, and never duplicate OHLCV or indicator values.
```

## Models

### Indicators
- market_indicators_5m
- market_indicators_15m
- market_indicators_30m
- market_indicators_1h
- market_indicators_1d

Materialization: incremental + MERGE

Primary key: (exchange, symbol, open_time)

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

## Adding New Features in the Future

1. Add a new macro (or extend existing category macro file) in `dbt/macros/gold/features/`.
2. Use the macro inside the appropriate category ephemeral model (`models/gold/features/<category>_features.sql`) as reference.
3. Add the column computation (via macro) inside the 5 `market_features_*` orchestration models (in the proper category CTE).
4. Add column entry + tests in `dbt/models/gold/gold.yml`.
5. Document the new feature in this file under the relevant category.
6. Add small commit, run `dbt compile && dbt run --select gold && dbt test --select gold`.

This guarantees one source of truth and consistency across all timeframes.

## Incremental Strategy

Similar to Silver and Indicators: reprocessing window (tf-dependent: 30d for 5m ... 400d for 1d) to allow recalculation when new or corrected data arrives.

## Testing

- not_null tests on keys (exchange, symbol, open_time) for all models.
- Basic coverage for feature models in gold.yml.
- Full validation via `dbt test --select gold`.

## Data Flow

Silver aggregated candles → Gold Indicators (no OHLCV dup)

Gold Indicators (+ Silver Candles where strictly needed) → Gold Features (only feature columns persisted)

Consumers (Signals / Feature Tables / trading bot) read from Gold Features (and Indicators when raw values needed) joined with Silver when full context required.