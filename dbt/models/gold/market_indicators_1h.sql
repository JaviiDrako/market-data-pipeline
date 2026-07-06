{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

WITH source AS (
    SELECT * FROM {{ ref('market_candles_1h') }}
    {% if is_incremental() %}
        WHERE open_time >= (SELECT COALESCE(MAX(open_time) - INTERVAL '90 days', TIMESTAMP '1970-01-01') FROM {{ this }})
    {% endif %}
)

SELECT 
    exchange, symbol, open_time,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 8 PRECEDING AND CURRENT ROW) AS ema_9,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) AS ema_21,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS ema_50,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS ema_200,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,
    AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS sma_200,
    NULL::numeric AS rsi_14, NULL::numeric AS macd, NULL::numeric AS macd_signal, NULL::numeric AS macd_histogram,
    NULL::numeric AS atr_14, NULL::numeric AS bb_upper, NULL::numeric AS bb_middle, NULL::numeric AS bb_lower, NULL::numeric AS adx_14
FROM source
{% if is_incremental() %}
WHERE open_time > (SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01') FROM {{ this }})
{% endif %}