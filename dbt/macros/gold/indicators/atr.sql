{% macro atr(period=14) %}
  AVG(
    GREATEST(
      high_price - low_price,
      ABS(high_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time)),
      ABS(low_price - LAG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time))
    )
  ) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW)
{% endmacro %}