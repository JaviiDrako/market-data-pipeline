{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

WITH source AS (
    SELECT * FROM {{ ref('market_candles_1d') }}
    {% if is_incremental() %}
        WHERE open_time >= (SELECT COALESCE(MAX(open_time) - INTERVAL '400 days', TIMESTAMP '1970-01-01') FROM {{ this }})
    {% endif %}
)

SELECT 
    exchange, symbol, open_time,
    {{ sma('close_price', 9) }} AS ema_9,
    {{ sma('close_price', 21) }} AS ema_21,
    {{ sma('close_price', 50) }} AS ema_50,
    {{ sma('close_price', 200) }} AS ema_200,
    {{ sma('close_price', 20) }} AS sma_20,
    {{ sma('close_price', 50) }} AS sma_50,
    {{ sma('close_price', 200) }} AS sma_200,
    NULL::numeric AS rsi_14,
    NULL::numeric AS macd, NULL::numeric AS macd_signal, NULL::numeric AS macd_histogram,
    NULL::numeric AS atr_14,
    NULL::numeric AS bb_upper, NULL::numeric AS bb_middle, NULL::numeric AS bb_lower,
    NULL::numeric AS adx_14
FROM source
{% if is_incremental() %}
WHERE open_time > (SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01') FROM {{ this }})
{% endif %}