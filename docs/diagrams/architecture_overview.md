# General Architecture

High-level view of the Market Data Pipeline platform.

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#1B4F72",
    "primaryTextColor": "#FFFFFF",
    "primaryBorderColor": "#154360",
    "lineColor": "#5D6D7E",
    "secondaryColor": "#D5F5E3",
    "tertiaryColor": "#FCF3CF",
    "fontFamily": "Inter, Segoe UI, sans-serif"
  },
  "flowchart": { "curve": "basis", "padding": 16 }
}}%%
flowchart TB
    classDef external fill:#5D6D7E,stroke:#2C3E50,color:#fff,stroke-width:2px
    classDef ingest fill:#1B4F72,stroke:#0E2F44,color:#fff,stroke-width:2px
    classDef warehouse fill:#117A65,stroke:#0B5345,color:#fff,stroke-width:2px
    classDef transform fill:#B7950B,stroke:#7D6608,color:#1C2833,stroke-width:2px
    classDef orch fill:#6C3483,stroke:#4A235A,color:#fff,stroke-width:2px
    classDef pending fill:#F5B7B1,stroke:#922B21,color:#1C2833,stroke-width:1px,stroke-dasharray: 5 4
    classDef config fill:#AED6F1,stroke:#2874A6,color:#1C2833,stroke-width:1px

    subgraph EXT["🌐 External"]
        API["Binance REST API"]
    end

    subgraph CFG["⚙️ Configuration"]
        YAML["config.yaml<br/>Settings"]
    end

    subgraph ING["🐍 Python Ingestion"]
        direction TB
        CLI["Binance Client"]
        EXT2["Extractor"]
        DQ["Data Quality"]
        BP["BronzePipeline<br/>incremental"]
        BSP["BootstrapPipeline<br/>historical"]
        LOAD["Bronze Loader"]
        MON["Pipeline Monitor"]
        CLI --> EXT2 --> DQ
        DQ --> BP
        DQ --> BSP
        BP --> LOAD
        BSP --> LOAD
        BP --> MON
        BSP --> MON
    end

    subgraph ORCH["⏱️ Orchestration"]
        AF_I["Airflow DAG<br/>incremental_market_data"]
        AF_B["Airflow DAG<br/>bootstrap_market_data"]
    end

    subgraph WH["🗄️ PostgreSQL Warehouse"]
        direction TB
        BR["bronze.*"]
        SV["silver.*"]
        GD["gold.*"]
        BR --> SV --> GD
    end

    subgraph DBT["🔧 Transformations"]
        DBT_B["dbt build<br/>staging → silver → gold"]
    end

    subgraph CONS["📦 Downstream consumers"]
        BI["BI Dashboards"]
        BOT["Trading Bot"]
        ML["Machine Learning"]
    end

    YAML -.->|symbols · history · schedule| ING
    API --> CLI
    AF_I -->|schedule| BP
    AF_B -->|manual| BSP
    LOAD --> BR
    AF_I --> DBT_B
    AF_B --> DBT_B
    DBT_B --> SV
    DBT_B --> GD
    GD -.-> BI
    GD -.-> BOT
    GD -.-> ML

    class API external
    class CLI,EXT2,DQ,BP,BSP,LOAD,MON ingest
    class BR,SV,GD warehouse
    class DBT_B transform
    class AF_I,AF_B orch
    class BI,BOT,ML pending
    class YAML config
```

**Legend**

| Style | Meaning |
|-------|---------|
| Solid blue | Implemented Python ingestion |
| Green | Warehouse layers |
| Purple | Airflow orchestration |
| Gold | dbt transformations |
| Dashed red | Pending product consumers (not in this repo) |
