WITH candles AS (
    SELECT
        '5m' AS timeframe,
        exchange,
        symbol,
        open_time,
        close_price
    FROM {{ ref('market_candles_5m') }}

    UNION ALL

    SELECT
        '1h' AS timeframe,
        exchange,
        symbol,
        open_time,
        close_price
    FROM {{ ref('market_candles_1h') }}
),

numbered AS (
    SELECT
        c.*,
        ROW_NUMBER() OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY open_time
        ) AS rn
    FROM candles c
),

numbered_with_max AS (
    SELECT
        n.*,
        MAX(rn) OVER (
            PARTITION BY timeframe, exchange, symbol
        ) AS max_rn
    FROM numbered n
),

indicator_reference AS (
    SELECT
        n.*,
        SUM(close_price * POWER(0.8461538461538461, max_rn - rn)) OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY rn
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / NULLIF(
            SUM(POWER(0.8461538461538461, max_rn - rn)) OVER (
                PARTITION BY timeframe, exchange, symbol
                ORDER BY rn
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            0
        ) AS ema12_reference,
        SUM(close_price * POWER(0.9259259259259259, max_rn - rn)) OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY rn
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / NULLIF(
            SUM(POWER(0.9259259259259259, max_rn - rn)) OVER (
                PARTITION BY timeframe, exchange, symbol
                ORDER BY rn
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            0
        ) AS ema26_reference,
        AVG(close_price) OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY open_time
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS bb_middle_reference,
        STDDEV(close_price) OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY open_time
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS bb_std_reference
    FROM numbered_with_max n
),

macd_reference AS (
    SELECT
        i.*,
        ema12_reference - ema26_reference AS macd_reference
    FROM indicator_reference i
),

reference_values AS (
    SELECT
        m.*,
        SUM(macd_reference * POWER(0.8, max_rn - rn)) OVER (
            PARTITION BY timeframe, exchange, symbol
            ORDER BY rn
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / NULLIF(
            SUM(POWER(0.8, max_rn - rn)) OVER (
                PARTITION BY timeframe, exchange, symbol
                ORDER BY rn
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            0
        ) AS macd_signal_reference
    FROM macd_reference m
),

materialized AS (
    SELECT '5m' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_5m') }}

    UNION ALL

    SELECT '1h' AS timeframe, exchange, symbol, open_time,
           macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower
    FROM {{ ref('market_indicators_1h') }}
),

comparison AS (
    SELECT
        m.timeframe,
        m.exchange,
        m.symbol,
        m.open_time,
        m.macd,
        r.macd_reference,
        m.macd_signal,
        r.macd_signal_reference,
        m.macd_histogram,
        r.macd_reference - r.macd_signal_reference AS macd_histogram_reference,
        m.bb_upper,
        r.bb_middle_reference + 2 * r.bb_std_reference AS bb_upper_reference,
        m.bb_middle,
        r.bb_middle_reference,
        m.bb_lower,
        r.bb_middle_reference - 2 * r.bb_std_reference AS bb_lower_reference
    FROM materialized m
    JOIN reference_values r
      ON r.timeframe = m.timeframe
     AND r.exchange = m.exchange
     AND r.symbol = m.symbol
     AND r.open_time = m.open_time
)

SELECT *
FROM comparison
WHERE (macd IS NULL) IS DISTINCT FROM (macd_reference IS NULL)
   OR (macd IS NOT NULL AND macd_reference IS NOT NULL
       AND ABS(macd - macd_reference) > 1e-8)
   OR (macd_signal IS NULL) IS DISTINCT FROM (macd_signal_reference IS NULL)
   OR (macd_signal IS NOT NULL AND macd_signal_reference IS NOT NULL
       AND ABS(macd_signal - macd_signal_reference) > 1e-8)
   OR (macd_histogram IS NULL) IS DISTINCT FROM (macd_histogram_reference IS NULL)
   OR (macd_histogram IS NOT NULL AND macd_histogram_reference IS NOT NULL
       AND ABS(macd_histogram - macd_histogram_reference) > 1e-8)
   OR (bb_upper IS NULL) IS DISTINCT FROM (bb_upper_reference IS NULL)
   OR (bb_upper IS NOT NULL AND bb_upper_reference IS NOT NULL
       AND ABS(bb_upper - bb_upper_reference) > 1e-8)
   OR (bb_middle IS NULL) IS DISTINCT FROM (bb_middle_reference IS NULL)
   OR (bb_middle IS NOT NULL AND bb_middle_reference IS NOT NULL
       AND ABS(bb_middle - bb_middle_reference) > 1e-8)
   OR (bb_lower IS NULL) IS DISTINCT FROM (bb_lower_reference IS NULL)
   OR (bb_lower IS NOT NULL AND bb_lower_reference IS NOT NULL
       AND ABS(bb_lower - bb_lower_reference) > 1e-8)
