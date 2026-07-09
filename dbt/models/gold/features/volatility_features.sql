{{ config(
    materialized='ephemeral'
) }}

-- Volatility Features (reusable implementation)
-- Consumes Gold market_indicators and Silver market_candles

WITH source AS (
    SELECT
        i.exchange,
        i.symbol,
        i.open_time,

        i.atr_14,
        i.bb_upper,
        i.bb_middle,
        i.bb_lower,

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

    {{ atr_pct() }} AS atr_pct,
    {{ rolling_std(20) }} AS rolling_std,

    {{ bollinger_width() }} AS bollinger_width,
    {{ bollinger_position() }} AS bollinger_position

FROM source
