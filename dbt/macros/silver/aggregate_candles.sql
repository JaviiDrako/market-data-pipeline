{% macro generate_candle_bucket(timestamp_col, interval_minutes) %}
    to_timestamp(
        floor(
            extract(epoch from {{ timestamp_col }}) / ({{ interval_minutes }} * 60)
        ) * ({{ interval_minutes }} * 60)
    )
{% endmacro %}


{% macro aggregate_ohlcv(source_relation, interval_minutes) %}
    WITH source_data AS (
        SELECT * FROM {{ source_relation }}
    ),

    bucketed AS (
        SELECT
            exchange,
            symbol,
            {{ generate_candle_bucket('open_time', interval_minutes) }} AS open_time,
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
        FROM source_data
    ),

    aggregated AS (
        SELECT
            exchange,
            symbol,
            open_time,
            (array_agg(close_time ORDER BY open_time DESC))[1] AS close_time,
            (array_agg(open_price ORDER BY open_time ASC))[1] AS open_price,
            max(high_price) AS high_price,
            min(low_price) AS low_price,
            (array_agg(close_price ORDER BY open_time DESC))[1] AS close_price,
            sum(volume) AS volume,
            sum(quote_asset_volume) AS quote_asset_volume,
            sum(number_of_trades) AS number_of_trades,
            sum(taker_buy_base_volume) AS taker_buy_base_volume,
            sum(taker_buy_quote_volume) AS taker_buy_quote_volume,
            max(ingested_at) AS ingested_at
        FROM bucketed
        GROUP BY
            exchange,
            symbol,
            open_time
    )

    SELECT * FROM aggregated
{% endmacro %}