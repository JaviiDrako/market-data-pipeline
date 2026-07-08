{% macro rsi_normalized() -%}
  ( rsi_14 - 50.0 ) / 50.0
{%- endmacro %}

{% macro macd_strength(price_column='close_price') -%}
  macd / NULLIF( {{ price_column }}, 0 ) * 100
{%- endmacro %}

{% macro macd_histogram_pct(price_column='close_price') -%}
  macd_histogram / NULLIF( {{ price_column }}, 0 ) * 100
{%- endmacro %}

{% macro price_change_pct(periods) -%}
  ( close_price - LAG(close_price, {{ periods }}) OVER (
      PARTITION BY exchange, symbol
      ORDER BY open_time
    )
  ) / NULLIF(
    LAG(close_price, {{ periods }}) OVER (
      PARTITION BY exchange, symbol
      ORDER BY open_time
    ), 0
  ) * 100
{%- endmacro %}
