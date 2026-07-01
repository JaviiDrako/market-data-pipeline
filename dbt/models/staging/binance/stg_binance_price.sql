SELECT
    'BINANCE' AS exchange,
    symbol,
    price,
    ingested_at
FROM {{ source('bronze', 'binance_price') }}