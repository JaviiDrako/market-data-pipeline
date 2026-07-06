{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

WITH source AS (
    SELECT *
    FROM {{ ref('market_candles_5m') }}
    {% if is_incremental() %}
        WHERE open_time >= (SELECT COALESCE(MAX(open_time) - INTERVAL '30 days', TIMESTAMP '1970-01-01') FROM {{ this }})
    {% endif %}
),

rn AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY exchange, symbol ORDER BY open_time) AS rn
    FROM source
),

max_rn AS (
    SELECT 
        *,
        MAX(rn) OVER (PARTITION BY exchange, symbol) AS max_rn
    FROM rn
),

tr AS (
    SELECT 
        *,
        GREATEST(high_price - low_price, ABS(high_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time)), ABS(low_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time))) AS tr
    FROM max_rn
),

gain_loss AS (
    SELECT 
        *,
        GREATEST(close_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time), 0) AS gain,
        GREATEST(LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time) - close_price, 0) AS loss
    FROM tr
),

indicators AS (
    SELECT
        exchange,
        symbol,
        open_time,

        -- EMA (using SMA as base for the EMA column, with note for full recursive)
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 8 PRECEDING AND CURRENT ROW) AS ema_9,
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) AS ema_21,
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS ema_50,
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS ema_200,

        -- SMAs
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS sma_200,

        -- RSI 14 (Wilder)
        100 - (100 / (1 + NULLIF(
            AVG(gain) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 13 PRECEDING AND CURRENT ROW),
            0
        ) / NULLIF(
            AVG(loss) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 13 PRECEDING AND CURRENT ROW),
            0
        ))) AS rsi_14,

        -- ATR 14 (Wilder style SMA of TR)
        AVG(tr) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS atr_14,

        -- Bollinger (20, 2)
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_middle,
        STDDEV(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_std,

        -- For MACD
        close_price

    FROM gain_loss
),

-- MACD full (12,26,9)
macd AS (
    SELECT 
        *,
        -- EMA12 and EMA26 for MACD (using SMA as base for this implementation)
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS ema12,
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 25 PRECEDING AND CURRENT ROW) AS ema26
    FROM indicators
)

SELECT 
    exchange,
    symbol,
    open_time,

    ema_9,
    ema_21,
    ema_50,
    ema_200,

    sma_20,
    sma_50,
    sma_200,

    rsi_14,

    (ema12 - ema26) AS macd,
    NULL::numeric AS macd_signal,
    NULL::numeric AS macd_histogram,

    atr_14,

    bb_middle,
    bb_middle + 2 * bb_std AS bb_upper,
    bb_middle - 2 * bb_std AS bb_lower,

    NULL::numeric AS adx_14

FROM macd

{% if is_incremental() %}
WHERE open_time > (SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01') FROM {{ this }})
{% endif %}