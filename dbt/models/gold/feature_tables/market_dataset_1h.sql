{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

-- Market Dataset 1h
-- Final consolidated Gold Feature Table.
-- Consumes ONLY market_indicators_1h + market_features_1h + market_signals_1h.
-- Contains keys + all Features + all Signals. No indicators, no OHLCV.
-- Extremely simple orchestration: no calculations.

WITH features AS (
    SELECT *
    FROM {{ ref('market_features_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

signals AS (
    SELECT *
    FROM {{ ref('market_signals_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

indicators AS (
    SELECT exchange, symbol, open_time
    FROM {{ ref('market_indicators_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
)

SELECT
    f.exchange,
    f.symbol,
    f.open_time,

    -- All Features (from features table)
    f.ema9_distance_pct,
    f.ema21_distance_pct,
    f.ema50_distance_pct,
    f.ema200_distance_pct,
    f.ema_alignment,
    f.ema_slope_9,
    f.ema_slope_21,
    f.ema_slope_50,
    f.price_vs_ema50_pct,
    f.price_vs_ema200_pct,
    f.rsi_normalized,
    f.macd_strength,
    f.macd_histogram_pct,
    f.price_change_5,
    f.price_change_10,
    f.price_change_20,
    f.atr_pct,
    f.rolling_std,
    f.bollinger_width,
    f.bollinger_position,
    f.candle_body_ratio,
    f.upper_wick_ratio,
    f.lower_wick_ratio,
    f.distance_to_20_high,
    f.distance_to_20_low,
    f.distance_to_50_high,
    f.distance_to_50_low,

    -- All Signals (from signals table)
    s.ema_bullish_alignment,
    s.ema_bearish_alignment,
    s.price_above_ema50,
    s.price_above_ema200,
    s.golden_cross,
    s.death_cross,
    s.rsi_overbought,
    s.rsi_oversold,
    s.rsi_recovering,
    s.macd_bullish_cross,
    s.macd_bearish_cross,
    s.macd_positive,
    s.high_volatility,
    s.low_volatility,
    s.bollinger_breakout_up,
    s.bollinger_breakout_down,
    s.new_20_high,
    s.new_20_low,
    s.new_50_high,
    s.new_50_low,
    s.breakout_confirmation

FROM features f
JOIN signals s
  USING (exchange, symbol, open_time)
JOIN indicators i
  USING (exchange, symbol, open_time)

{% if is_incremental() %}
WHERE f.open_time > (
    SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01')
    FROM {{ this }}
)
{% endif %}
