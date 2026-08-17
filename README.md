# GridWatch — UK Transmission Network Analytics

A data engineering project analyzing how network load and grid conditions across Great Britain's transmission regions relate to product engagement and retention risk for a mock B2B SaaS platform serving distribution network operator (DNO) asset planning teams.

## The problem

Do the customer accounts responsible for the highest-stress network regions actually engage with GridWatch's monitoring platform — or are the regions that most need proactive oversight also the ones at highest risk of the customer not renewing? This project investigates that question end-to-end: real grid data in, a business recommendation out.

## What it does

GridWatch ingests real transmission-level electricity data for Great Britain, blends it with synthetic subscriber/usage data representing a fictional SaaS customer base, and analyzes the relationship between regional network conditions and customer engagement/renewal risk.

## Architecture

```
Data sources (real APIs + mock generator)
        │
        ▼
Ingestion — AWS Lambda + Step Functions (scheduled polling → raw S3)
        │
        ▼
Transform — AWS Glue (clean, partition → curated S3, Parquet)
        │
        ▼
Load — BigQuery (star schema)
        │
        ▼
Analyze & report — SQL + business case
```

## Tech stack

- **AWS**: Lambda, Step Functions, S3, Glue
- **Google Cloud**: BigQuery
- **Python**: data generation, ingestion logic
- **SQL**: analytical modeling and querying

## Data sources

- **Real**: [NESO Carbon Intensity API](https://carbonintensity.org.uk) — regional demand, generation mix, and carbon intensity across Great Britain's 14 official grid regions. Licensed under CC BY 4.0.
- **Mock**: synthetic customer accounts, users, and product usage events, generated with Python and `faker`, joined to real regions via a shared `region_id`. Account placement, size (`properties_served`), and engagement patterns are weighted using real regional customer-density figures (UK Power Networks, SSEN) and the real Scotland wind-curtailment dynamic, rather than arbitrary/uniform assumptions — see the build guide's Phase 1 addendum for details and sources.

## Project status

- [x] Environment setup (AWS, BigQuery, Git/GitHub, VS Code)
- [x] Phase 1 — Mock customer/usage data generation (450 accounts, region-weighted, seasonally-aware)
- [ ] Phase 2 — Real data ingestion (Lambda + Step Functions)
- [ ] Phase 3 — Transform (Glue)
- [ ] Phase 4 — Load into BigQuery
- [ ] Phase 5 — SQL analysis
- [ ] Phase 6 — Business case write-up

## Repository structure

```
gridwatch/
├── ingestion/      Lambda functions, Step Functions definitions
├── transform/      Glue ETL scripts
├── infra/          Step Functions state machine, Lambda deploy config & script, EventBridge definitions
├── warehouse/      BigQuery schema and analytical SQL
├── mock_data/      Synthetic data generator
├── notebooks/      Exploratory analysis
├── docs/           Architecture notes and business case write-up
└── tests/          Tests (added once there's logic worth testing)
```

## Getting started

```
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python mock_data/generate_data.py
```

## Findings & business case

See [`docs/business_case.md`](docs/business_case.md) once Phase 6 is complete.

## Data attribution

Grid data provided by the National Energy System Operator (NESO) under the Carbon Intensity API, licensed CC BY 4.0.
