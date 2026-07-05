{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'open_time'],
    incremental_strategy='merge'
) }}

{% set interval_minutes = 30 %}
{% set interval_label = '30m' %}

WITH base AS (
    SELECT *
    FROM {{ ref('market_candles') }}
    WHERE interval = '1m'
    {% if is_incremental() %}
        AND open_time >= (
            SELECT COALESCE(
                MAX(open_time) - INTERVAL '7 days',
                TIMESTAMP '1970-01-01'
            )
            FROM {{ this }}
        )
    {% endif %}
),

aggregated AS (
    SELECT *
    FROM (
        {{ aggregate_ohlcv('base', interval_minutes, interval_label) }}
    ) agg
    WHERE (
        SELECT COUNT(*)
        FROM {{ ref('market_candles') }} src
        WHERE src.interval = '1m'
          AND src.exchange = agg.exchange
          AND src.symbol = agg.symbol
          AND src.open_time >= agg.open_time
          AND src.open_time < agg.open_time + INTERVAL '{{ interval_minutes }} minutes'
    ) = {{ interval_minutes }}
),

with_attributes AS (
    {{ add_candle_attributes('aggregated') }}
)

SELECT * FROM with_attributes