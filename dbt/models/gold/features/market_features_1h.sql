{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

-- Market Features 1h
-- Orchestrates union of all feature categories.
-- Consumes ONLY Gold Indicators + Silver Candles (no direct Bronze, no indicator recalc).
-- Stores only keys + computed features (no OHLCV / indicator duplication).

WITH base_indicators AS (
    SELECT *
    FROM {{ ref('market_indicators_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

base_candles AS (
    SELECT
        exchange,
        symbol,
        open_time,
        close_price,
        high_price,
        low_price,
        body_size,
        upper_wick,
        lower_wick,
        candle_range
    FROM {{ ref('market_candles_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

source AS (
    SELECT
        i.exchange,
        i.symbol,
        i.open_time,

        -- From indicators
        i.ema_9,
        i.ema_21,
        i.ema_50,
        i.ema_200,
        i.rsi_14,
        i.macd,
        i.macd_histogram,
        i.atr_14,
        i.bb_upper,
        i.bb_middle,
        i.bb_lower,

        -- From candles (for price action + changes)
        c.close_price,
        c.high_price,
        c.low_price,
        c.body_size,
        c.upper_wick,
        c.lower_wick,
        c.candle_range
    FROM base_indicators i
    JOIN base_candles c
      USING (exchange, symbol, open_time)
),

trend_features AS (
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
),

momentum_features AS (
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
),

volatility_features AS (
    SELECT
        exchange,
        symbol,
        open_time,

        {{ atr_pct() }} AS atr_pct,
        {{ rolling_std(20) }} AS rolling_std,

        {{ bollinger_width() }} AS bollinger_width,
        {{ bollinger_position() }} AS bollinger_position
    FROM source
),

price_action_features AS (
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
)

SELECT
    t.exchange,
    t.symbol,
    t.open_time,

    -- Trend
    t.ema9_distance_pct,
    t.ema21_distance_pct,
    t.ema50_distance_pct,
    t.ema200_distance_pct,

    t.ema_alignment,

    t.ema_slope_9,
    t.ema_slope_21,
    t.ema_slope_50,

    t.price_vs_ema50_pct,
    t.price_vs_ema200_pct,

    -- Momentum
    m.rsi_normalized,

    m.macd_strength,
    m.macd_histogram_pct,

    m.price_change_5,
    m.price_change_10,
    m.price_change_20,

    -- Volatility
    v.atr_pct,
    v.rolling_std,

    v.bollinger_width,
    v.bollinger_position,

    -- Price Action
    p.candle_body_ratio,
    p.upper_wick_ratio,
    p.lower_wick_ratio,

    p.distance_to_20_high,
    p.distance_to_20_low,

    p.distance_to_50_high,
    p.distance_to_50_low

FROM trend_features t
JOIN momentum_features m
  USING (exchange, symbol, open_time)
JOIN volatility_features v
  USING (exchange, symbol, open_time)
JOIN price_action_features p
  USING (exchange, symbol, open_time)

{% if is_incremental() %}
WHERE t.open_time > (
    SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01')
    FROM {{ this }}
)
{% endif %}
