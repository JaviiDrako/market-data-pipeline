# Gold Layer - Technical Indicators

## Purpose

The Gold layer computes and persists technical indicators on top of the Silver aggregated candles.

Gold is optimized for consumption by the algorithmic trading bot.

## Architecture

Gold reads exclusively from Silver.

```
Silver (market_candles_5m, 15m, 30m, 1h, 1d)
    ↓
Gold (market_indicators_5m, 15m, 30m, 1h, 1d)
```

## Models

- market_indicators_5m
- market_indicators_15m
- market_indicators_30m
- market_indicators_1h
- market_indicators_1d

Materialization: incremental + MERGE

Primary key: (exchange, symbol, open_time)

## Indicators Implemented

- EMA (9, 21, 50, 200) - using weighted exponential smoothing (finite history EMA)
- SMA (20, 50, 200)
- RSI (14) - Wilder implementation
- MACD (macd, signal, histogram) - full standard implementation
- ATR (14) - with True Range
- Bollinger Bands (upper, middle, lower)

## Implementation

Gold models act as orchestration layers:
- They read from the corresponding Silver timeframe model.
- They prepare common CTEs (row numbering, True Range, gain/loss for RSI, etc.).
- They call reusable dbt macros for each indicator calculation.

Indicator implementations live in `dbt/macros/gold/indicators/`:
- ema.sql, sma.sql, rsi.sql, atr.sql, bollinger.sql, macd.sql

Each indicator has exactly one implementation. New indicators can be added by creating a new macro and calling it from the Gold models.

This ensures maintainability and avoids duplication across timeframes.

ADX was removed entirely (no placeholders).

## Incremental Strategy

Similar to Silver: reprocessing window to allow recalculation when new or corrected Silver data arrives.

## Testing

Basic not_null tests on key columns.

## Data Flow

Silver aggregated candles → Gold indicators (no OHLCV duplication in Gold).

Consumers join Gold with Silver for full candle + indicator data.