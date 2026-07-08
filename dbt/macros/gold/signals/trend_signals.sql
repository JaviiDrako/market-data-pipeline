{% macro ema_bullish_alignment() -%}
  (ema_alignment = 1)
{%- endmacro %}

{% macro ema_bearish_alignment() -%}
  (ema_alignment = 0)
{%- endmacro %}

{% macro price_above_ema50() -%}
  (price_vs_ema50_pct > 0)
{%- endmacro %}

{% macro price_above_ema200() -%}
  (price_vs_ema200_pct > 0)
{%- endmacro %}

{% macro golden_cross() -%}
  (ema_50 > ema_200 AND LAG(ema_50, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time) <= LAG(ema_200, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time))
{%- endmacro %}

{% macro death_cross() -%}
  (ema_50 < ema_200 AND LAG(ema_50, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time) >= LAG(ema_200, 1) OVER (PARTITION BY exchange, symbol ORDER BY open_time))
{%- endmacro %}
