{{ config(
    materialized='ephemeral'
) }}

-- Trend Features (reusable implementation)
-- Consumes Gold market_indicators and Silver market_candles
-- Used as reference; actual orchestration in market_features_* models

WITH source AS (
    SELECT
        i.exchange,
        i.symbol,
        i.open_time,

        i.ema_9,
        i.ema_21,
        i.ema_50,
        i.ema_200,

        c.close_price,
        c.high_price,
        c.low_price
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

    {{ ema_distance_pct('ema_9') }} AS ema9_distance_pct,
    {{ ema_distance_pct('ema_21') }} AS ema21_distance_pct,
    {{ ema_distance_pct('ema_50') }} AS ema50_distance_pct,
    {{ ema_distance_pct('ema_200') }} AS ema200_distance_pct,

    {{ ema_alignment() }} AS ema_alignment,

    {{ ema_slope('ema_9') }} AS ema_slope_9,
    {{ ema_slope('ema_21') }} AS ema_slope_21,
    {{ ema_slope('ema_50') }} AS ema_slope_50,

    {{ price_vs_ema_pct('ema_50') }} AS price_vs_ema50_pct,
    {{ price_vs_ema_pct('ema_200') }} AS price_vs_ema200_pct

FROM source
