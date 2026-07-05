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

- EMA (9, 21, 50, 200)
- SMA (20, 50, 200)
- RSI (14)
- MACD (macd, signal, histogram) - base implementation
- ATR (14)
- Bollinger Bands (middle, upper, lower)
- ADX (14) - placeholder

## Macros

Located in `dbt/macros/gold/indicators/`:

- sma.sql
- ema.sql
- rsi.sql
- atr.sql
- bollinger.sql
- macd.sql
- adx.sql

## Incremental Strategy

Similar to Silver: reprocessing window to allow recalculation when new or corrected Silver data arrives.

## Testing

Basic not_null tests on key columns.

## Data Flow

Silver aggregated candles → Gold indicators (no OHLCV duplication in Gold).

Consumers join Gold with Silver for full candle + indicator data.