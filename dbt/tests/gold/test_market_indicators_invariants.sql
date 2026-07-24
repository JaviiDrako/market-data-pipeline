WITH indicators AS (
    SELECT '5m' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram,
           bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_5m') }}

    UNION ALL

    SELECT '15m' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram,
           bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_15m') }}

    UNION ALL

    SELECT '30m' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram,
           bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_30m') }}

    UNION ALL

    SELECT '1h' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram,
           bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_1h') }}

    UNION ALL

    SELECT '1d' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram,
           bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_1d') }}
),

ordered AS (
    SELECT
        i.*,
        ROW_NUMBER() OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY open_time
        ) AS row_number_in_symbol
    FROM indicators i
),

violations AS (
    SELECT
        timeframe,
        exchange,
        symbol,
        open_time,
        'macd_histogram_formula' AS violation
    FROM ordered
    WHERE macd IS NOT NULL
      AND macd_signal IS NOT NULL
      AND macd_histogram IS NOT NULL
      AND ABS(macd_histogram - (macd - macd_signal)) > 1e-9

    UNION ALL

    SELECT
        timeframe,
        exchange,
        symbol,
        open_time,
        'bollinger_upper_order' AS violation
    FROM ordered
    WHERE bb_upper IS NOT NULL
      AND bb_middle IS NOT NULL
      AND bb_upper < bb_middle

    UNION ALL

    SELECT
        timeframe,
        exchange,
        symbol,
        open_time,
        'bollinger_lower_order' AS violation
    FROM ordered
    WHERE bb_lower IS NOT NULL
      AND bb_middle IS NOT NULL
      AND bb_middle < bb_lower

    UNION ALL

    SELECT
        timeframe,
        exchange,
        symbol,
        open_time,
        'bollinger_missing_after_warmup' AS violation
    FROM ordered
    WHERE row_number_in_symbol >= 20
      AND (bb_upper IS NULL OR bb_lower IS NULL)
)

SELECT *
FROM violations
