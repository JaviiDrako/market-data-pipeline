{% macro atr_pct(price_column='close_price') -%}
  atr_14 / NULLIF( {{ price_column }}, 0 ) * 100
{%- endmacro %}

{% macro rolling_std(periods=20, price_column='close_price') -%}
  STDDEV( {{ price_column }} ) OVER (
    PARTITION BY exchange, symbol
    ORDER BY open_time
    ROWS BETWEEN {{ periods - 1 }} PRECEDING AND CURRENT ROW
  ) / NULLIF( {{ price_column }}, 0 ) * 100
{%- endmacro %}

{% macro bollinger_width() -%}
  ( bb_upper - bb_lower ) / NULLIF( bb_middle, 0 ) * 100
{%- endmacro %}

{% macro bollinger_position(price_column='close_price') -%}
  ( {{ price_column }} - bb_lower ) / NULLIF( (bb_upper - bb_lower), 0 )
{%- endmacro %}
