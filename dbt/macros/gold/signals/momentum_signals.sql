{% macro rsi_overbought() -%}
  (rsi_14 >= 70)
{%- endmacro %}

{% macro rsi_oversold() -%}
  (rsi_14 <= 30)
{%- endmacro %}

{% macro rsi_recovering() -%}
  (rsi_14 > LAG(rsi_14, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time) AND rsi_14 > 30)
{%- endmacro %}

{% macro macd_bullish_cross() -%}
  (macd > macd_signal AND LAG(macd, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time) <= LAG(macd_signal, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time))
{%- endmacro %}

{% macro macd_bearish_cross() -%}
  (macd < macd_signal AND LAG(macd, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time) >= LAG(macd_signal, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time))
{%- endmacro %}

{% macro macd_positive() -%}
  (macd > 0)
{%- endmacro %}
