{% macro bollinger_middle(period=20) -%}
  AVG(close_price) OVER (
    PARTITION BY exchange, symbol 
    ORDER BY open_time 
    ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
  )
{%- endmacro %}

{% macro bollinger_std(period=20) -%}
  STDDEV(close_price) OVER (
    PARTITION BY exchange, symbol 
    ORDER BY open_time 
    ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
  )
{%- endmacro %}