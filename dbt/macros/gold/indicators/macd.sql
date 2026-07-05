{% macro macd(fast=12, slow=26, signal=9) %}
  /* MACD logic is implemented in the model for proper layering of EMAs */
  NULL AS macd,
  NULL AS macd_signal,
  NULL AS macd_histogram
{% endmacro %}