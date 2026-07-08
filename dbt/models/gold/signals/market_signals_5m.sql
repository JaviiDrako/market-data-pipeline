{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

-- Market Signals 5m
-- Orchestrates union of all signal categories.
-- Consumes ONLY Gold Features + Gold Indicators (no recalculation, no Bronze/Staging).
-- Stores only keys + boolean/integer signals.

WITH base_features AS (
    SELECT *
    FROM {{ ref('market_features_5m') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '30 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

base_indicators AS (
    SELECT
        exchange,
        symbol,
        open_time,
        ema_9,
        ema_21,
        ema_50,
        ema_200,
        rsi_14,
        macd,
        macd_signal
    FROM {{ ref('market_indicators_5m') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '30 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

source AS (
    SELECT
        f.exchange,
        f.symbol,
        f.open_time,

        -- From features (for most signals)
        f.ema_alignment,
        f.price_vs_ema50_pct,
        f.price_vs_ema200_pct,
        f.rsi_normalized,
        f.macd_strength,
        f.macd_histogram_pct,
        f.atr_pct,
        f.bollinger_width,
        f.bollinger_position,
        f.distance_to_20_high,
        f.distance_to_20_low,
        f.distance_to_50_high,
        f.distance_to_50_low,
        f.price_change_5,

        -- From indicators (for crosses + classic thresholds)
        i.ema_50,
        i.ema_200,
        i.rsi_14,
        i.macd,
        i.macd_signal
    FROM base_features f
    JOIN base_indicators i
      USING (exchange, symbol, open_time)
),

trend_signals AS (
    SELECT
        exchange,
        symbol,
        open_time,

        {{ ema_bullish_alignment() }} AS ema_bullish_alignment,
        {{ ema_bearish_alignment() }} AS ema_bearish_alignment,
        {{ price_above_ema50() }} AS price_above_ema50,
        {{ price_above_ema200() }} AS price_above_ema200,
        {{ golden_cross() }} AS golden_cross,
        {{ death_cross() }} AS death_cross
    FROM source
),

momentum_signals AS (
    SELECT
        exchange,
        symbol,
        open_time,

        {{ rsi_overbought() }} AS rsi_overbought,
        {{ rsi_oversold() }} AS rsi_oversold,
        {{ rsi_recovering() }} AS rsi_recovering,
        {{ macd_bullish_cross() }} AS macd_bullish_cross,
        {{ macd_bearish_cross() }} AS macd_bearish_cross,
        {{ macd_positive() }} AS macd_positive
    FROM source
),

volatility_signals AS (
    SELECT
        exchange,
        symbol,
        open_time,

        {{ high_volatility() }} AS high_volatility,
        {{ low_volatility() }} AS low_volatility,
        {{ bollinger_breakout_up() }} AS bollinger_breakout_up,
        {{ bollinger_breakout_down() }} AS bollinger_breakout_down
    FROM source
),

breakout_signals AS (
    SELECT
        exchange,
        symbol,
        open_time,

        {{ new_20_high() }} AS new_20_high,
        {{ new_20_low() }} AS new_20_low,
        {{ new_50_high() }} AS new_50_high,
        {{ new_50_low() }} AS new_50_low,
        {{ breakout_confirmation() }} AS breakout_confirmation
    FROM source
)

SELECT
    t.exchange,
    t.symbol,
    t.open_time,

    -- Trend Signals
    t.ema_bullish_alignment,
    t.ema_bearish_alignment,
    t.price_above_ema50,
    t.price_above_ema200,
    t.golden_cross,
    t.death_cross,

    -- Momentum Signals
    m.rsi_overbought,
    m.rsi_oversold,
    m.rsi_recovering,
    m.macd_bullish_cross,
    m.macd_bearish_cross,
    m.macd_positive,

    -- Volatility Signals
    v.high_volatility,
    v.low_volatility,
    v.bollinger_breakout_up,
    v.bollinger_breakout_down,

    -- Breakout Signals
    b.new_20_high,
    b.new_20_low,
    b.new_50_high,
    b.new_50_low,
    b.breakout_confirmation

FROM trend_signals t
JOIN momentum_signals m
  USING (exchange, symbol, open_time)
JOIN volatility_signals v
  USING (exchange, symbol, open_time)
JOIN breakout_signals b
  USING (exchange, symbol, open_time)

{% if is_incremental() %}
WHERE t.open_time > (
    SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01')
    FROM {{ this }}
)
{% endif %}
