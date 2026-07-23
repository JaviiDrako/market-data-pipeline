{{ config(
    materialized='view'
) }}

-- =============================================================================
-- market_candles_bi
-- =============================================================================
-- Business Intelligence consumption view for Power BI OHLCV visualizations.
--
-- Unifies all Silver aggregated candle models with a timeframe label.
-- Does NOT replace the per-timeframe Silver candle models and does not add
-- transformation logic beyond the UNION ALL and timeframe projection.
-- =============================================================================

SELECT
    exchange,
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
    ingested_at,
    candle_direction,
    body_size,
    upper_wick,
    lower_wick,
    candle_range,
    typical_price,
    ohlc_average,
    '5m' AS timeframe
FROM {{ ref('market_candles_5m') }}

UNION ALL

SELECT
    exchange,
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
    ingested_at,
    candle_direction,
    body_size,
    upper_wick,
    lower_wick,
    candle_range,
    typical_price,
    ohlc_average,
    '15m' AS timeframe
FROM {{ ref('market_candles_15m') }}

UNION ALL

SELECT
    exchange,
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
    ingested_at,
    candle_direction,
    body_size,
    upper_wick,
    lower_wick,
    candle_range,
    typical_price,
    ohlc_average,
    '30m' AS timeframe
FROM {{ ref('market_candles_30m') }}

UNION ALL

SELECT
    exchange,
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
    ingested_at,
    candle_direction,
    body_size,
    upper_wick,
    lower_wick,
    candle_range,
    typical_price,
    ohlc_average,
    '1h' AS timeframe
FROM {{ ref('market_candles_1h') }}

UNION ALL

SELECT
    exchange,
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
    ingested_at,
    candle_direction,
    body_size,
    upper_wick,
    lower_wick,
    candle_range,
    typical_price,
    ohlc_average,
    '1d' AS timeframe
FROM {{ ref('market_candles_1d') }}
