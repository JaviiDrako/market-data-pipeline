# Medallion Architecture

Data products and refinement path inside the PostgreSQL warehouse.

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "fontFamily": "Inter, Segoe UI, sans-serif",
    "lineColor": "#566573"
  },
  "flowchart": { "curve": "basis", "padding": 18 }
}}%%
flowchart TB
    classDef bronze fill:#CD6155,stroke:#922B21,color:#fff,stroke-width:2px
    classDef silver fill:#5DADE2,stroke:#1A5276,color:#1C2833,stroke-width:2px
    classDef gold fill:#F4D03F,stroke:#B7950B,color:#1C2833,stroke-width:2px
    classDef control fill:#AF7AC5,stroke:#6C3483,color:#fff,stroke-width:2px
    classDef consumer fill:#D5D8DC,stroke:#5D6D7E,color:#1C2833,stroke-width:1px,stroke-dasharray: 4 3

    subgraph B["🥉 BRONZE — raw · provider-specific · auditable"]
        direction LR
        BK[("binance_klines")]
        BP[("binance_price")]
        BT[("binance_ticker_24h")]
        PR[("pipeline_runs")]
        CS[("configured_symbols")]
    end

    subgraph S["🥈 SILVER — standardized · multi-timeframe"]
        direction TB
        STG["stg_binance_*<br/>views"]
        MC[("market_candles 1m")]
        MS[("market_snapshot")]
        AGG[("market_candles<br/>5m · 15m · 30m · 1h · 1d")]
        STG --> MC
        STG --> MS
        MC --> AGG
    end

    subgraph G["🥇 GOLD — intelligence for consumers"]
        direction TB
        IND[("market_indicators_*")]
        FEAT[("market_features_*")]
        SIG[("market_signals_*")]
        DS[("market_dataset_*<br/>keys + features + signals")]
        IND --> FEAT --> SIG --> DS
    end

    subgraph C["🔮 Future consumers"]
        BI["BI"]
        BOT["Trading Bot"]
        ML["ML / Backtest"]
    end

    BK --> STG
    BP --> STG
    BT --> STG
    AGG --> IND
    DS -.-> BI
    DS -.-> BOT
    DS -.-> ML

    class BK,BP,BT bronze
    class PR,CS control
    class STG,MC,MS,AGG silver
    class IND,FEAT,SIG,DS gold
    class BI,BOT,ML consumer
```

### Refinement contract

```mermaid
%%{init: { "theme": "base" }}%%
flowchart LR
    classDef b fill:#CD6155,stroke:#922B21,color:#fff
    classDef s fill:#5DADE2,stroke:#1A5276,color:#1C2833
    classDef g1 fill:#F7DC6F,stroke:#B7950B,color:#1C2833
    classDef g2 fill:#F4D03F,stroke:#B7950B,color:#1C2833
    classDef g3 fill:#F1C40F,stroke:#B7950B,color:#1C2833
    classDef g4 fill:#D4AC0D,stroke:#7D6608,color:#1C2833

    A["API payload"] --> B["Bronze facts"]
    B --> C["Silver candles"]
    C --> D["Indicators"]
    D --> E["Features"]
    E --> F["Signals"]
    F --> G["Feature tables"]

    class A,B b
    class C s
    class D g1
    class E g2
    class F g3
    class G g4
```

| Layer | Responsibility | Typical materialization |
|-------|----------------|-------------------------|
| Bronze | Preserve provider raw shape + audit | Physical SQL tables |
| Silver | Normalize + aggregate closed candles | dbt view + incremental MERGE |
| Gold | Compute & persist intelligence | dbt incremental MERGE |
