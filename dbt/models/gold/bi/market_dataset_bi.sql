{{ config(
    materialized='view'
) }}

-- =============================================================================
-- market_dataset_bi
-- =============================================================================
-- Business Intelligence consumption view for Power BI.
--
-- Unifies all Gold Feature Tables (market_dataset_*) with a timeframe label.
-- Does NOT replace the per-timeframe market_dataset_* models.
-- Trading Bot, ML and other consumers continue to use market_dataset_* directly.
-- =============================================================================

SELECT
    *,
    '5m' AS timeframe
FROM {{ ref('market_dataset_5m') }}

UNION ALL

SELECT
    *,
    '15m' AS timeframe
FROM {{ ref('market_dataset_15m') }}

UNION ALL

SELECT
    *,
    '30m' AS timeframe
FROM {{ ref('market_dataset_30m') }}

UNION ALL

SELECT
    *,
    '1h' AS timeframe
FROM {{ ref('market_dataset_1h') }}

UNION ALL

SELECT
    *,
    '1d' AS timeframe
FROM {{ ref('market_dataset_1d') }}
