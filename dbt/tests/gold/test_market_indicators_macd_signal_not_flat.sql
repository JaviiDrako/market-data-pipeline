WITH indicators AS (
    SELECT '5m' AS timeframe, exchange, symbol, open_time, macd, macd_signal
    FROM {{ ref('market_indicators_5m') }}

    UNION ALL

    SELECT '15m' AS timeframe, exchange, symbol, open_time, macd, macd_signal
    FROM {{ ref('market_indicators_15m') }}

    UNION ALL

    SELECT '30m' AS timeframe, exchange, symbol, open_time, macd, macd_signal
    FROM {{ ref('market_indicators_30m') }}

    UNION ALL

    SELECT '1h' AS timeframe, exchange, symbol, open_time, macd, macd_signal
    FROM {{ ref('market_indicators_1h') }}

    UNION ALL

    SELECT '1d' AS timeframe, exchange, symbol, open_time, macd, macd_signal
    FROM {{ ref('market_indicators_1d') }}
),

latest_rows AS (
    SELECT
        i.*,
        ROW_NUMBER() OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY open_time DESC
        ) AS latest_row_number
    FROM indicators i
),

distribution AS (
    SELECT
        timeframe,
        COUNT(*) FILTER (
            WHERE macd IS NOT NULL
              AND macd_signal IS NOT NULL
        ) AS comparable_rows,
        COUNT(*) FILTER (
            WHERE macd IS NOT NULL
              AND macd_signal IS NOT NULL
              AND ABS(macd - macd_signal) > 1e-9
        ) AS non_flat_rows
    FROM latest_rows
    WHERE latest_row_number <= 20
    GROUP BY timeframe
)

SELECT *
FROM distribution
WHERE comparable_rows >= 20
  AND non_flat_rows = 0
