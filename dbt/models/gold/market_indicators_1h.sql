{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

WITH source AS (
    SELECT *
    FROM {{ ref('market_candles_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

-- Row number and max_rn for weighting
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

-- True Range
tr AS (
    SELECT 
        *,
        GREATEST(
            high_price - low_price,
            ABS(high_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time)),
            ABS(low_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time))
        ) AS tr
    FROM max_rn
),

-- Gain/Loss for RSI
gain_loss AS (
    SELECT 
        *,
        GREATEST(close_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time), 0) AS gain,
        GREATEST(LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time) - close_price, 0) AS loss
    FROM tr
),

-- Indicators with correct EMA using weighted average for the window (correct finite EMA)
indicators AS (
    SELECT
        exchange,
        symbol,
        open_time,

        -- EMA9 (k=0.2, factor=0.8)
        SUM(close_price * power(0.8, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
        NULLIF( SUM(power(0.8, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ema_9,

        -- EMA21 (factor=0.90909)
        SUM(close_price * power(0.90909, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
        NULLIF( SUM(power(0.90909, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ema_21,

        -- EMA50 (factor=0.96078)
        SUM(close_price * power(0.96078, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
        NULLIF( SUM(power(0.96078, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ema_50,

        -- EMA200 (factor=0.99005)
        SUM(close_price * power(0.99005, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
        NULLIF( SUM(power(0.99005, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ema_200,

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

        -- ATR 14
        AVG(tr) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS atr_14,

        -- Bollinger
        AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_middle,
        STDDEV(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_std,

        close_price,
        rn,
        max_rn

    FROM gain_loss
),

-- MACD
macd AS (
    SELECT 
        *,
        -- EMA12
        SUM(close_price * power(0.84615, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
        NULLIF(SUM(power(0.84615, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ema12,
        -- EMA26
        SUM(close_price * power(0.92593, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
        NULLIF(SUM(power(0.92593, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ema26
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
    SUM((ema12 - ema26) * power(0.8, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
    NULLIF( SUM(power(0.8, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0 ) AS macd_signal,
    (ema12 - ema26) - (
      SUM((ema12 - ema26) * power(0.8, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) /
      NULLIF( SUM(power(0.8, max_rn - rn)) OVER (PARTITION BY exchange, symbol ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0 )
    ) AS macd_histogram,

    atr_14,

    bb_middle,
    bb_middle + 2 * bb_std AS bb_upper,
    bb_middle - 2 * bb_std AS bb_lower

FROM macd

{% if is_incremental() %}
WHERE open_time > (SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01') FROM {{ this }})
{% endif %}