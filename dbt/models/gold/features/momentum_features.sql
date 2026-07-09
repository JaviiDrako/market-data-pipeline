{{ config(
    materialized='ephemeral'
) }}

-- Momentum Features (reusable implementation)
-- Consumes Gold market_indicators and Silver market_candles

WITH source AS (
    SELECT
        i.exchange,
        i.symbol,
        i.open_time,

        i.rsi_14,
        i.macd,
        i.macd_histogram,

        c.close_price
    FROM {{ ref('market_indicators_5m') }} i
    JOIN {{ ref('market_candles_5m') }} c
      ON i.exchange = c.exchange
     AND i.symbol = c.symbol
     AND i.open_time = c.open_time
)

SELECT
    exchange,
    symbol,
    open_time,

    {{ rsi_normalized() }} AS rsi_normalized,

    {{ macd_strength() }} AS macd_strength,
    {{ macd_histogram_pct() }} AS macd_histogram_pct,

    {{ price_change_pct(5) }} AS price_change_5,
    {{ price_change_pct(10) }} AS price_change_10,
    {{ price_change_pct(20) }} AS price_change_20

FROM source
