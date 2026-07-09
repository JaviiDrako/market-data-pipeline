{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'snapshot_time'],
    incremental_strategy='merge'
) }}

-- Always one row per (exchange, symbol): latest price + latest ticker only.
-- Prevents MERGE "cannot affect row a second time" from multi-row joins.

WITH latest_price AS (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY exchange, symbol
                ORDER BY ingested_at DESC
            ) AS rn
        FROM {{ ref('stg_binance_price') }}
    ) ranked
    WHERE rn = 1
),

latest_ticker AS (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY exchange, symbol
                ORDER BY ingested_at DESC
            ) AS rn
        FROM {{ ref('stg_binance_ticker_24h') }}
    ) ranked
    WHERE rn = 1
)

SELECT
    p.exchange,
    p.symbol,
    p.price,
    t.price_change,
    t.price_change_percent,
    t.weighted_avg_price,
    t.prev_close_price,
    t.last_price,
    t.last_qty,
    t.bid_price,
    t.bid_qty,
    t.ask_price,
    t.ask_qty,
    t.open_price,
    t.high_price,
    t.low_price,
    t.volume,
    t.quote_volume,
    t.open_time,
    t.close_time,
    t.first_id,
    t.last_id,
    t.count,
    GREATEST(
        p.ingested_at,
        t.ingested_at
    ) AS snapshot_time

FROM latest_price p

INNER JOIN latest_ticker t
    ON p.exchange = t.exchange
   AND p.symbol = t.symbol
