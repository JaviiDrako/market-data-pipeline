{% macro ema(column, period) %}
  /* 
    Calculates EMA using standard formula.
    Seeds with SMA of the first 'period' values, then applies smoothing.
    Assumes data is ordered and gaps are handled upstream in Silver.
  */
  CASE 
    WHEN ROW_NUMBER() OVER (PARTITION BY exchange, symbol ORDER BY open_time) < {{ period }} 
      THEN NULL
    WHEN ROW_NUMBER() OVER (PARTITION BY exchange, symbol ORDER BY open_time) = {{ period }} 
      THEN AVG({{ column }}) OVER (
        PARTITION BY exchange, symbol 
        ORDER BY open_time 
        ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
      )
    ELSE 
      {{ column }} * (2.0 / ({{ period }} + 1)) + 
      LAG(ema_{{ period }}, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time) * (1 - 2.0 / ({{ period }} + 1))
  END
{% endmacro %}