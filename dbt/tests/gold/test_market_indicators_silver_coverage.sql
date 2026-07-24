WITH silver_keys AS (
    SELECT '5m' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_candles_5m') }}
    UNION
    SELECT '15m' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_candles_15m') }}
    UNION
    SELECT '30m' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_candles_30m') }}
    UNION
    SELECT '1h' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_candles_1h') }}
    UNION
    SELECT '1d' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_candles_1d') }}
),

gold_keys AS (
    SELECT '5m' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_indicators_5m') }}
    UNION
    SELECT '15m' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_indicators_15m') }}
    UNION
    SELECT '30m' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_indicators_30m') }}
    UNION
    SELECT '1h' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_indicators_1h') }}
    UNION
    SELECT '1d' AS timeframe, exchange, symbol, open_time FROM {{ ref('market_indicators_1d') }}
)

SELECT
    s.timeframe,
    s.exchange,
    s.symbol,
    s.open_time
FROM silver_keys s
LEFT JOIN gold_keys g
  ON g.timeframe = s.timeframe
 AND g.exchange = s.exchange
 AND g.symbol = s.symbol
 AND g.open_time = s.open_time
WHERE g.exchange IS NULL
