# 🖥️ Device Asset Intelligence Platform

> An end-to-end data engineering portfolio project simulating an enterprise IT asset lifecycle pipeline — from synthetic data generation to analytics-ready reporting — using Python, FastAPI, AWS S3, PostgreSQL, and SQL.

---

## 👤 Author

**Dr. Miguel Rodriguez Saldana, DCS**  
Business Intelligence Engineer | Data Engineering Practitioner  
Arlington, TX | [GitHub](https://github.com/miguelbda21)

---

## 📌 Project Overview

This project demonstrates a production-style data engineering pipeline focused on **computing device asset management** — one of the most critical operational domains in enterprise IT. It models the full asset lifecycle from procurement through end-of-life (EOL), enriched with financial data including purchase cost, depreciation, and budget exposure.

The platform is designed to answer real business questions:
- Which devices are approaching end-of-life in the next 90, 180, or 365 days?
- What is the total replacement cost exposure by department and fiscal quarter?
- Which devices are past EOL but still actively deployed (a compliance and security risk)?
- How does actual device spend compare to budgeted refresh cycles?

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Synthetic Data Generator                    │
│         (Python + Faker — 200 device records)           │
└────────────────────┬────────────────────────────────────┘
                     │ boto3
                     ▼
┌─────────────────────────────────────────────────────────┐
│              AWS S3 (Raw Landing Zone)                   │
│   s3://bucket/raw/assets/                               │
│   s3://bucket/raw/financials/                           │
└────────────────────┬────────────────────────────────────┘
                     │ Python ETL (pandas + SQLAlchemy)
                     ▼
┌─────────────────────────────────────────────────────────┐
│           AWS RDS PostgreSQL (Warehouse)                 │
│   dim_device | dim_financial | fact_asset_events        │
│   fact_eol_forecast | vw_eol_dashboard                  │
└────────────────────┬────────────────────────────────────┘
                     │ FastAPI REST API
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application (Local / EC2)           │
│   POST /assets          → Ingest device records         │
│   GET  /assets          → Query all assets              │
│   GET  /assets/{id}     → Single asset detail           │
│   GET  /eol/upcoming    → Devices expiring in 90/180d   │
│   GET  /financials      → Budget & cost summary         │
│   POST /pipeline/run    → Trigger ETL pipeline          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Tableau Public Dashboard                    │
│   EOL Risk by Department | Budget Exposure by Quarter   │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
device-asset-intelligence-platform/
│
├── api/                          ← FastAPI application
│   ├── main.py                   ← App entry point
│   ├── dependencies.py           ← DB + S3 connection setup
│   ├── routers/
│   │   ├── assets.py             ← GET/POST /assets endpoints
│   │   ├── eol.py                ← GET /eol/upcoming endpoint
│   │   ├── financials.py         ← GET /financials endpoint
│   │   └── pipeline.py           ← POST /pipeline/run endpoint
│   └── models/
│       ├── asset.py              ← Pydantic device model
│       └── financial.py          ← Pydantic financial model
│
├── etl/                          ← Data pipeline
│   ├── extract.py                ← Read raw data from S3
│   ├── transform.py              ← Clean, calculate EOL + depreciation
│   └── load.py                   ← Write to RDS PostgreSQL
│
├── data_generator/
│   └── generate_assets.py        ← Generate 200 synthetic device records
│
├── data/
│   ├── raw/                      ← S3 landing zone mirror (local)
│   ├── staged/                   ← Cleaned and standardized data
│   └── warehouse/                ← Analytics-ready output
│
├── sql/
│   ├── ddl/                      ← CREATE TABLE scripts
│   ├── transformations/          ← Staging → warehouse SQL logic
│   └── analytics/                ← KPI views and mart queries
│
├── tests/
│   ├── test_api.py               ← FastAPI endpoint tests
│   └── test_etl.py               ← Pipeline unit tests
│
├── .github/
│   └── workflows/
│       └── ci.yml                ← GitHub Actions: run tests on push
│
├── .env.example                  ← Credential template (safe for GitHub)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🗃️ Data Model

### `dim_device` — Core Asset Dimension

| Field | Type | Description |
|---|---|---|
| `asset_id` | UUID | Primary key |
| `asset_tag` | VARCHAR | Enterprise asset identifier |
| `device_type` | VARCHAR | Laptop / Desktop / Server / Mobile |
| `make` | VARCHAR | Dell, HP, Lenovo, Apple, etc. |
| `model` | VARCHAR | Specific model name |
| `serial_number` | VARCHAR | Unique hardware identifier |
| `purchase_date` | DATE | Start of depreciation |
| `purchase_cost` | DECIMAL | Original cost in USD |
| `end_of_life_date` | DATE | ⭐ Most critical field |
| `days_to_eol` | INT | Computed: EOL date minus today |
| `eol_risk_tier` | VARCHAR | Critical / Warning / Healthy |
| `department` | VARCHAR | Business unit assignment |
| `assigned_user` | VARCHAR | Current device owner |
| `location` | VARCHAR | Office / Remote / Data Center |
| `status` | VARCHAR | Active / In-Repair / Retired |

### `dim_financial` — Financial Dimension

| Field | Type | Description |
|---|---|---|
| `financial_id` | UUID | Primary key |
| `asset_id` | UUID | Foreign key to dim_device |
| `budget_code` | VARCHAR | Budget allocation code |
| `fiscal_year` | INT | Budget year |
| `depreciation_years` | INT | Useful life (3-5 years) |
| `current_book_value` | DECIMAL | Straight-line depreciation calc |
| `replacement_budget_flag` | BOOLEAN | Flagged for next refresh cycle |

### `fact_eol_forecast` — EOL Forecasting Fact Table

| Field | Type | Description |
|---|---|---|
| `forecast_id` | UUID | Primary key |
| `asset_id` | UUID | Foreign key |
| `eol_quarter` | VARCHAR | e.g., Q3-2025 |
| `replacement_cost` | DECIMAL | Projected cost to replace |
| `department` | VARCHAR | For departmental roll-up |
| `risk_tier` | VARCHAR | Critical / Warning / Healthy |

---

## 📊 Key KPIs This Platform Produces

- **Devices within 90 / 180 / 365 days of EOL** by department
- **Total replacement cost exposure** by fiscal quarter
- **Average device age** by type and department
- **Budget vs. actual spend** on device refresh cycles
- **Devices past EOL still actively deployed** (compliance risk metric)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API Framework | FastAPI + Uvicorn |
| Data Processing | pandas, numpy |
| AWS Integration | boto3 |
| Database ORM | SQLAlchemy |
| Database | PostgreSQL (AWS RDS) |
| Cloud Storage | AWS S3 |
| Data Validation | Pydantic v2 |
| Synthetic Data | Faker |
| Testing | pytest + httpx |
| Code Quality | black, ruff, mypy |
| CI/CD | GitHub Actions |
| Visualization | Tableau Public |
| Version Control | Git + GitHub |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- AWS account (Free Tier)
- PostgreSQL (AWS RDS free tier)
- PyCharm (recommended IDE)

### 1. Clone the Repository

```bash
git clone https://github.com/miguelbda21/device-asset-intelligence-platform.git
cd device-asset-intelligence-platform
```

### 2. Create a Virtual Environment

In PyCharm: **File → New Project → Virtualenv**

Or via terminal:
```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your real AWS and database credentials.

### 5. Generate Synthetic Data

```bash
python data_generator/generate_assets.py
```

### 6. Run the ETL Pipeline

```bash
python etl/extract.py
python etl/transform.py
python etl/load.py
```

### 7. Start the FastAPI Server

```bash
uvicorn api.main:app --reload
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

---

## 🧪 Running Tests

```bash
pytest tests/
```

GitHub Actions will also run tests automatically on every push to `main`.

---

## 🔗 Related Projects

- [`de-project-template`](https://github.com/miguelbda21/de-project-template) — Reusable data engineering project template
- [`enterprise-asset-lifecycle-data-platform`](https://github.com/miguelbda21/enterprise-asset-lifecycle-data-platform) — Previous CMDB simulation project

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

This project was built as part of a structured self-study program to transition from Business Intelligence Engineering into Data Engineering, applying 15+ years of enterprise analytics experience at Texas Health Resources to modern cloud-native data pipeline practices.
```
