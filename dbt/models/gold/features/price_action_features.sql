{{ config(
    materialized='ephemeral'
) }}

-- Price Action Features (reusable implementation)
-- Consumes Silver market_candles (via attributes) + indicators if needed for context
-- Note: body/wick/range come from silver candle attributes (no duplication)

WITH source AS (
    SELECT
        c.exchange,
        c.symbol,
        c.open_time,

        c.close_price,
        c.high_price,
        c.low_price,
        c.body_size,
        c.upper_wick,
        c.lower_wick,
        c.candle_range
    FROM {{ ref('market_candles_5m') }} c
    -- Note: for pure price action could avoid indicators, but per architecture we prefer indicators where possible
)

SELECT
    exchange,
    symbol,
    open_time,

    {{ candle_body_ratio() }} AS candle_body_ratio,
    {{ upper_wick_ratio() }} AS upper_wick_ratio,
    {{ lower_wick_ratio() }} AS lower_wick_ratio,

    {{ distance_to_n_high(20) }} AS distance_to_20_high,
    {{ distance_to_n_low(20) }} AS distance_to_20_low,

    {{ distance_to_n_high(50) }} AS distance_to_50_high,
    {{ distance_to_n_low(50) }} AS distance_to_50_low

FROM source
