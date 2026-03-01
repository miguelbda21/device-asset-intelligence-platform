🖥️ Device Asset Intelligence Platform

An end-to-end cloud-native data engineering portfolio project simulating an enterprise IT asset lifecycle pipeline — from synthetic data generation to analytics-ready reporting — using Python, FastAPI, AWS S3, PostgreSQL (AWS RDS), and SQL.

👤 Author

Dr. Miguel Rodriguez Saldana, DCS
Business Intelligence Engineer | Data Engineering Practitioner
Arlington, TX
GitHub: https://github.com/miguelbda21

📌 Project Overview

This project demonstrates a production-style data engineering platform focused on enterprise device asset lifecycle management — one of the most critical operational domains in IT organizations.

It models the full asset lifecycle from procurement through end-of-life (EOL), enriched with financial data including purchase cost, depreciation, and budget exposure.

🔎 Business Questions This Platform Answers

Which devices are approaching end-of-life in the next 90, 180, or 365 days?

What is the total replacement cost exposure by department and fiscal quarter?

Which devices are past EOL but still actively deployed (compliance risk)?

How does device spend compare to planned refresh cycles?

🏗️ Architecture
Synthetic Data Generator (Faker)
        │
        ▼
AWS S3 (Raw Landing Zone)
        │
        ▼
Python ETL (pandas + SQLAlchemy)
        │
        ▼
AWS RDS PostgreSQL (Warehouse)
        │
        ▼
FastAPI REST API
        │
        ▼
Tableau Public Dashboard
🏛️ Project Structure (Production Layout)

All application code resides inside the src/ directory to ensure:

Clean packaging

Predictable imports

Test isolation

Docker/EC2/Lambda compatibility

CI/CD readiness

device-asset-intelligence-platform/
│
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── routers/
│   │   │   ├── assets.py
│   │   │   ├── eol.py
│   │   │   ├── financials.py
│   │   │   └── pipeline.py
│   │   └── models/
│   │       ├── asset.py
│   │       └── financial.py
│   │
│   ├── etl/
│   │   ├── extract.py
│   │   ├── transform.py
│   │   ├── load.py
│   │   └── pipeline.py
│   │
│   ├── data_generator/
│   │   └── generate_assets.py
│   │
│   └── db/
│       ├── config.py
│       └── session.py
│
├── data/
│   ├── raw/
│   ├── staging/
│   └── warehouse/
│
├── sql/
│   ├── ddl/
│   ├── transformations/
│   └── analytics/
│
├── tests/
│   ├── test_api.py
│   ├── test_etl.py
│   └── check_db_connection.py
│
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
🗃️ Data Model
dim_device — Core Asset Dimension
Field	Description
asset_id	UUID primary key
asset_tag	Enterprise asset identifier
device_type	Laptop / Desktop / Server / Mobile
make	Manufacturer
model	Model name
serial_number	Hardware identifier
purchase_date	Start of depreciation
purchase_cost	Original cost
end_of_life_date	Calculated EOL
days_to_eol	Derived metric
eol_risk_tier	Critical / Warning / Healthy
department	Business unit
assigned_user	Current owner
location	Office / Remote / Data Center
status	Active / Retired / In-Repair
📊 Key KPIs Produced

Devices within 90 / 180 / 365 days of EOL

Total replacement cost exposure by fiscal quarter

Average device age by department

Budget vs. actual device refresh spend

Devices past EOL still actively deployed

🛠️ Tech Stack
Layer	Technology
Language	Python 3.11
API	FastAPI + Uvicorn
ETL	pandas + SQLAlchemy
Cloud	AWS S3 + AWS RDS
Database	PostgreSQL
Validation	Pydantic v2
Testing	pytest + httpx
CI/CD	GitHub Actions
Visualization	Tableau Public
Version Control	Git + GitHub