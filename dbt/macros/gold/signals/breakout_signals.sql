{% macro new_20_high() -%}
  (distance_to_20_high <= 0.05)
{%- endmacro %}

{% macro new_20_low() -%}
  (distance_to_20_low <= 0.05)
{%- endmacro %}

{% macro new_50_high() -%}
  (distance_to_50_high <= 0.05)
{%- endmacro %}

{% macro new_50_low() -%}
  (distance_to_50_low <= 0.05)
{%- endmacro %}

{% macro breakout_confirmation() -%}
  ((distance_to_20_high <= 0.05 OR distance_to_50_high <= 0.05) AND (price_change_5 > 0 OR ema_alignment = 1))
{%- endmacro %}
