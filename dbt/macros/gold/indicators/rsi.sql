{% macro rsi(period=14) %}
  100 - (100 / (1 + 
    NULLIF(
      AVG(GREATEST(close_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time), 0)) 
        OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW),
      0
    ) / 
    NULLIF(
      AVG(GREATEST(LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time) - close_price, 0)) 
        OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW),
      0
    )
  ))
{% endmacro %}