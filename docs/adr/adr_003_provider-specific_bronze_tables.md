# ADR-003: Store Raw Data in Provider-Specific Bronze Tables

## Status

Accepted

---

## Context

Different market data providers expose different APIs and response formats.

Attempting to normalize provider responses during ingestion increases complexity and may result in information loss.

---

## Decision

Each provider stores its raw data in dedicated Bronze tables.

Examples include:

- bronze.binance_klines
- bronze.binance_current_price
- bronze.binance_ticker_24h

Future providers will introduce their own Bronze tables.

Data normalization is deferred to the Silver layer.

---

## Consequences

### Positive

- No information loss.
- Easier onboarding of new providers.
- Bronze remains a faithful representation of source systems.
- Simplifies debugging.

### Negative

- Duplicate concepts may exist across providers.
- Silver transformations become responsible for standardization.