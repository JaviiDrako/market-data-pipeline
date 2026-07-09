CREATE SCHEMA IF NOT EXISTS bronze;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n
            ON n.oid = t.typnamespace
        WHERE t.typname = 'pipeline_status'
          AND n.nspname = 'bronze'
    ) THEN
        CREATE TYPE bronze.pipeline_status AS ENUM ('running', 'success', 'failed');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
    pipeline_run_id BIGSERIAL PRIMARY KEY,
    dag_run_id VARCHAR(255) NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status bronze.pipeline_status,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    rows_updated INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (rows_inserted >= 0),
    CHECK (rows_updated >= 0)
);

CREATE TABLE IF NOT EXISTS bronze.binance_klines (
    pipeline_run_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(20,8) NOT NULL,
    high_price NUMERIC(20,8) NOT NULL,
    low_price NUMERIC(20,8) NOT NULL,
    close_price NUMERIC(20,8) NOT NULL,
    volume NUMERIC(28,8) NOT NULL,
    quote_asset_volume NUMERIC(28,8) NOT NULL,
    number_of_trades INTEGER NOT NULL,
    taker_buy_base_volume NUMERIC(28,8) NOT NULL,
    taker_buy_quote_volume NUMERIC(28,8) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_binance_klines PRIMARY KEY (symbol, open_time),
    CONSTRAINT fk_binance_klines_pipeline_run_id
        FOREIGN KEY (pipeline_run_id)
        REFERENCES bronze.pipeline_runs (pipeline_run_id),
    CHECK (open_price >= 0),
    CHECK (high_price >= 0),
    CHECK (low_price >= 0),
    CHECK (close_price >= 0),
    CHECK (volume >= 0),
    CHECK (quote_asset_volume >= 0),
    CHECK (number_of_trades >= 0),
    CHECK (taker_buy_base_volume >= 0),
    CHECK (taker_buy_quote_volume >= 0)
);

CREATE INDEX IF NOT EXISTS idx_binance_klines_symbol_open_time
    ON bronze.binance_klines (symbol, open_time);

CREATE TABLE IF NOT EXISTS bronze.binance_price (
    pipeline_run_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price NUMERIC(20,8) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_binance_price PRIMARY KEY (symbol, ingested_at),
    CONSTRAINT fk_binance_price_pipeline_run_id
        FOREIGN KEY (pipeline_run_id)
        REFERENCES bronze.pipeline_runs (pipeline_run_id),
    CHECK (price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_binance_price_symbol_ingested_at
    ON bronze.binance_price (symbol, ingested_at);

CREATE TABLE IF NOT EXISTS bronze.binance_ticker_24h (
    pipeline_run_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price_change NUMERIC(20,8) NOT NULL,
    price_change_percent NUMERIC(20,8) NOT NULL,
    weighted_avg_price NUMERIC(20,8) NOT NULL,
    prev_close_price NUMERIC(20,8) NOT NULL,
    last_price NUMERIC(20,8) NOT NULL,
    last_qty NUMERIC(28,8) NOT NULL,
    bid_price NUMERIC(20,8) NOT NULL,
    bid_qty NUMERIC(28,8) NOT NULL,
    ask_price NUMERIC(20,8) NOT NULL,
    ask_qty NUMERIC(28,8) NOT NULL,
    open_price NUMERIC(20,8) NOT NULL,
    high_price NUMERIC(20,8) NOT NULL,
    low_price NUMERIC(20,8) NOT NULL,
    volume NUMERIC(28,8) NOT NULL,
    quote_volume NUMERIC(28,8) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,
    first_id BIGINT NOT NULL,
    last_id BIGINT NOT NULL,
    count INTEGER NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_binance_ticker_24h PRIMARY KEY (symbol, ingested_at),
    CONSTRAINT fk_binance_ticker_24h_pipeline_run_id
        FOREIGN KEY (pipeline_run_id)
        REFERENCES bronze.pipeline_runs (pipeline_run_id),
    CHECK (weighted_avg_price >= 0),
    CHECK (prev_close_price >= 0),
    CHECK (last_price >= 0),
    CHECK (last_qty >= 0),
    CHECK (bid_price >= 0),
    CHECK (bid_qty >= 0),
    CHECK (ask_price >= 0),
    CHECK (ask_qty >= 0),
    CHECK (open_price >= 0),
    CHECK (high_price >= 0),
    CHECK (low_price >= 0),
    CHECK (volume >= 0),
    CHECK (quote_volume >= 0),
    CHECK (first_id >= 0),
    CHECK (last_id >= 0),
    CHECK (count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_binance_ticker_24h_symbol_ingested_at
    ON bronze.binance_ticker_24h (symbol, ingested_at);

-- Operational control table for bootstrap / symbol lifecycle.
-- No foreign keys: intentionally decoupled from market data tables.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n
            ON n.oid = t.typnamespace
        WHERE t.typname = 'bootstrap_status'
          AND n.nspname = 'bronze'
    ) THEN
        CREATE TYPE bronze.bootstrap_status AS ENUM (
            'pending',
            'running',
            'completed',
            'failed'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS bronze.configured_symbols (
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    history_days INTEGER NOT NULL DEFAULT 365,
    bootstrap_status bronze.bootstrap_status NOT NULL DEFAULT 'pending',
    last_bootstrap_open_time TIMESTAMPTZ,
    bootstrap_started_at TIMESTAMPTZ,
    bootstrap_completed_at TIMESTAMPTZ,
    last_incremental_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (exchange, symbol),
    CHECK (history_days > 0)
);

CREATE INDEX IF NOT EXISTS idx_configured_symbols_bootstrap_status
    ON bronze.configured_symbols (bootstrap_status)
    WHERE enabled = TRUE;
