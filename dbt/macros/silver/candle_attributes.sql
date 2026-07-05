{% macro add_candle_attributes(model) %}
    SELECT
        *,
        CASE
            WHEN close_price > open_price THEN 1
            WHEN close_price < open_price THEN -1
            ELSE 0
        END AS candle_direction,

        ABS(close_price - open_price) AS body_size,

        high_price - GREATEST(open_price, close_price) AS upper_wick,

        LEAST(open_price, close_price) - low_price AS lower_wick,

        high_price - low_price AS candle_range,

        (high_price + low_price + close_price) / 3 AS typical_price,

        (open_price + high_price + low_price + close_price) / 4 AS ohlc_average

    FROM {{ model }}
{% endmacro %}