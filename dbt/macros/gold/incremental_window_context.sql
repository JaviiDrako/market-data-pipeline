{% macro gold_incremental_window_context(candles_relation) -%}
all_candles AS (
    SELECT *
    FROM {{ candles_relation }}
)
{% if is_incremental() %}
,
existing_max AS (
    SELECT
        exchange,
        symbol,
        MAX(open_time) AS max_open_time
    FROM {{ this }}
    GROUP BY exchange, symbol
),

new_rows AS (
    SELECT c.*
    FROM all_candles c
    LEFT JOIN existing_max e
      ON e.exchange = c.exchange
     AND e.symbol = c.symbol
    WHERE e.exchange IS NULL
       OR c.open_time > e.max_open_time
       OR NOT EXISTS (
            SELECT 1
            FROM {{ this }} existing
            WHERE existing.exchange = c.exchange
              AND existing.symbol = c.symbol
              AND existing.open_time = c.open_time
       )
),

affected_keys AS (
    SELECT DISTINCT
        exchange,
        symbol
    FROM new_rows
),

source AS (
    SELECT c.*
    FROM all_candles c
    JOIN affected_keys k
      ON k.exchange = c.exchange
     AND k.symbol = c.symbol
)
{% else %}
,
new_rows AS (
    SELECT *
    FROM all_candles
),

source AS (
    SELECT *
    FROM all_candles
)
{% endif %}
{%- endmacro %}
