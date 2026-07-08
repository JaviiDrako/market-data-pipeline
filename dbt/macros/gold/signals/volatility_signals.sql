{% macro high_volatility() -%}
  (atr_pct > 1.5 OR bollinger_width > 4.0)
{%- endmacro %}

{% macro low_volatility() -%}
  (atr_pct < 0.6 AND bollinger_width < 2.0)
{%- endmacro %}

{% macro bollinger_breakout_up() -%}
  (bollinger_position > 1.0)
{%- endmacro %}

{% macro bollinger_breakout_down() -%}
  (bollinger_position < 0.0)
{%- endmacro %}
