{{ config(
    materialized='incremental',
    unique_key=['exchange', 'symbol', 'interval', 'open_time'],
    incremental_strategy='merge'
) }}

SELECT
    exchange,
    symbol,
    '1m' AS interval,
    open_time,
    close_time,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    quote_asset_volume,
    number_of_trades,
    taker_buy_base_volume,
    taker_buy_quote_volume,
    ingested_at
FROM {{ ref('stg_binance_klines') }}

{% if is_incremental() %}

WHERE open_time >
(
    SELECT COALESCE(MAX(open_time), TIMESTAMP '1970-01-01')
    FROM {{ this }}
)

{% endif %}