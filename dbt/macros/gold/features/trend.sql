{% macro ema_distance_pct(ema_column, price_column='close_price') -%}
  ( {{ price_column }} - {{ ema_column }} ) / NULLIF( {{ ema_column }}, 0 ) * 100
{%- endmacro %}

{% macro ema_alignment() -%}
  CASE
    WHEN ema_9 > ema_21
     AND ema_21 > ema_50
     AND ema_50 > ema_200
    THEN 1 ELSE 0
  END
{%- endmacro %}

{% macro ema_slope(ema_column, periods=1) -%}
  ( {{ ema_column }} - LAG({{ ema_column }}, {{ periods }}) OVER (
      PARTITION BY exchange, symbol
      ORDER BY open_time
    )
  ) / NULLIF(
    LAG({{ ema_column }}, {{ periods }}) OVER (
      PARTITION BY exchange, symbol
      ORDER BY open_time
    ), 0
  ) * 100
{%- endmacro %}

{% macro price_vs_ema_pct(ema_column, price_column='close_price') -%}
  ( {{ price_column }} - {{ ema_column }} ) / NULLIF( {{ ema_column }}, 0 ) * 100
{%- endmacro %}
