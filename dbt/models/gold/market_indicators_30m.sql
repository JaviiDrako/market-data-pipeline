{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

WITH source AS (
    SELECT *
    FROM {{ ref('market_candles_30m') }}
    {% if is_incremental() %}
        WHERE open_time >= (
            SELECT COALESCE(MAX(open_time) - INTERVAL '60 days', TIMESTAMP '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
),

-- Row number and max_rn for weighting (common for EMAs and MACD signal)
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

-- True Range (common for ATR)
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

-- Gain/Loss for RSI (common)
gain_loss AS (
    SELECT 
        *,
        GREATEST(close_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time), 0) AS gain,
        GREATEST(LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time) - close_price, 0) AS loss
    FROM tr
),

-- Indicators (orchestration - call macros)
indicators AS (
    SELECT
        exchange,
        symbol,
        open_time,

        {{ ema('close_price', 9) }} AS ema_9,
        {{ ema('close_price', 21) }} AS ema_21,
        {{ ema('close_price', 50) }} AS ema_50,
        {{ ema('close_price', 200) }} AS ema_200,

        {{ sma('close_price', 20) }} AS sma_20,
        {{ sma('close_price', 50) }} AS sma_50,
        {{ sma('close_price', 200) }} AS sma_200,

        {{ rsi(14) }} AS rsi_14,

        {{ atr(14) }} AS atr_14,

        {{ bollinger_middle(20) }} AS bb_middle,
        {{ bollinger_std(20) }} AS bb_std,

        close_price,
        rn,
        max_rn

    FROM gain_loss
),

-- MACD base (reuses ema macro for ema12 and ema26)
macd_base AS (
    SELECT 
        *,
        {{ ema('close_price', 12) }} AS ema12,
        {{ ema('close_price', 26) }} AS ema26
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
    {{ macd_signal(9) }} AS macd_signal,
    (ema12 - ema26) - {{ macd_signal(9) }} AS macd_histogram,

    atr_14,

    bb_middle,
    bb_middle + 2 * {{ bollinger_std(20) }} AS bb_upper,
    bb_middle - 2 * {{ bollinger_std(20) }} AS bb_lower

FROM macd_base

{% if is_incremental() %}
WHERE open_time > (
    SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01')
    FROM {{ this }}
)
{% endif %}