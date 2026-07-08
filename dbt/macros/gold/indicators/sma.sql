{% macro sma(column, period) -%}
  AVG({{ column }}) OVER (
    PARTITION BY exchange, symbol 
    ORDER BY open_time 
    ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
  )
{%- endmacro %}