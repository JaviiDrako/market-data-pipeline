{% macro candle_body_ratio() -%}
  body_size / NULLIF( candle_range, 0 )
{%- endmacro %}

{% macro upper_wick_ratio() -%}
  upper_wick / NULLIF( candle_range, 0 )
{%- endmacro %}

{% macro lower_wick_ratio() -%}
  lower_wick / NULLIF( candle_range, 0 )
{%- endmacro %}

{% macro distance_to_n_high(periods) -%}
  (
    MAX(high_price) OVER (
      PARTITION BY exchange, symbol
      ORDER BY open_time
      ROWS BETWEEN {{ periods - 1 }} PRECEDING AND CURRENT ROW
    ) - close_price
  ) / NULLIF( close_price, 0 ) * 100
{%- endmacro %}

{% macro distance_to_n_low(periods) -%}
  (
    close_price - MIN(low_price) OVER (
      PARTITION BY exchange, symbol
      ORDER BY open_time
      ROWS BETWEEN {{ periods - 1 }} PRECEDING AND CURRENT ROW
    )
  ) / NULLIF( close_price, 0 ) * 100
{%- endmacro %}
