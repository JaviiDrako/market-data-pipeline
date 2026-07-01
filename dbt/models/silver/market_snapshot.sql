{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'snapshot_time'],
    incremental_strategy='merge'
) }}

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

FROM {{ ref('stg_binance_price') }} p

INNER JOIN {{ ref('stg_binance_ticker_24h') }} t
    ON p.exchange = t.exchange
   AND p.symbol = t.symbol