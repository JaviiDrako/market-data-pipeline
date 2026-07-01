SELECT
    'BINANCE' AS exchange,
    symbol,
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
FROM {{ source('bronze', 'binance_klines') }}