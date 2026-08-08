# Business Intelligence

## Purpose

The `bi/` directory contains the Business Intelligence and Analytics consumption
layer for the market-data platform. It documents the tools that consume the
analytical warehouse without moving business logic out of the Medallion
pipeline.

The design keeps the warehouse and its Gold consumption views reusable. The
same analytical foundation can therefore support Power BI today and additional
BI or BI-as-Code implementations in the future.

## Current Implementation

Power BI is the current BI implementation. It is versioned as a PBIP project
with a PBIR report definition, a TMDL semantic model, persisted DAX measures,
and documentation screenshots.

See the [Power BI Analytics Dashboard](power-bi/README.md) documentation for
the report architecture, semantic model, report pages, and local usage.

## Data Consumption Layer

The current implementation consumes curated views from the Gold schema:

- `gold.market_dataset_bi` exposes feature and signal records for analytical
  exploration.
- `gold.market_candles_bi` exposes unified OHLCV records for price and candle
  analysis.

These views are the BI-facing contract. They do not replace the canonical Gold
tables or the upstream Bronze and Silver layers.

## Directory Structure

```text
bi/
├── README.md
└── power-bi/
    ├── Market Data Dashboard/
    │   ├── Market Data BI.Report/
    │   └── Market Data BI.SemanticModel/
    ├── Market Data BI.pbip
    ├── README.md
    └── screenshots/
```

## Future BI Implementations

Future consumers such as Evidence, Rill, Tableau, or other analytical tools can
be added under `bi/` as separate implementations. They are not part of the
current repository yet; any future implementation should consume the same
warehouse contracts and preserve the separation between data transformation and
analytics presentation.
