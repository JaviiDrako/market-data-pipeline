{% macro ema(column, period) -%}
  {% set k = 2.0 / (period + 1) %}
  {% set factor = 1 - k %}
  SUM( {{ column }} * power({{ factor }}, max_rn - rn) ) OVER (
    PARTITION BY exchange, symbol 
    ORDER BY rn 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) /
  NULLIF(
    SUM( power({{ factor }}, max_rn - rn) ) OVER (
      PARTITION BY exchange, symbol 
      ORDER BY rn 
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 
    0
  )
{%- endmacro %}