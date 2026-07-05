{% macro bollinger(period=20, std_dev=2) %}
  AVG(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW) AS bb_middle,
  STDDEV(close_price) OVER (PARTITION BY exchange, symbol ORDER BY open_time ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW) AS bb_std
{% endmacro %}