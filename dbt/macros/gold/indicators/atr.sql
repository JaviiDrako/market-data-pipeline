{% macro atr(period=14) -%}
  AVG(tr) OVER (
    PARTITION BY exchange, symbol 
    ORDER BY open_time 
    ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
  )
{%- endmacro %}