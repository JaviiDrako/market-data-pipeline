{% macro rsi(period=14) -%}
  100 - (100 / (1 + NULLIF(
    AVG(gain) OVER (
      PARTITION BY exchange, symbol 
      ORDER BY open_time 
      ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
    ), 0
  ) / NULLIF(
    AVG(loss) OVER (
      PARTITION BY exchange, symbol 
      ORDER BY open_time 
      ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
    ), 0
  )))
{%- endmacro %}