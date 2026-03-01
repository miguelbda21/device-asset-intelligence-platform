"""
load.py
-------
Loads transformed device data from the local warehouse
folder into AWS RDS PostgreSQL database.

Creates tables if they don't exist, then loads data
using upsert logic (insert or update on conflict).

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

import os
import pandas as pd
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Load environment variables ────────────────────────
load_dotenv()

# ── Force project root as working directory ───────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Database Connection ───────────────────────────────

def get_db_engine():
    """Create and return a SQLAlchemy engine for PostgreSQL."""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")

    connection_string = (
        f"postgresql+psycopg2://{db_user}:{db_pass}"
        f"@{db_host}:{db_port}/{db_name}"
        f"?sslmode=require"
    )

    engine = create_engine(connection_string)
    return engine


# ── Create Tables ─────────────────────────────────────

def create_tables(engine) -> None:
    """
    Create the dim_device table if it doesn't exist.
    Safe to run multiple times — uses IF NOT EXISTS.
    """
    print("  🔧 Creating tables if not exist...")

    create_dim_device = """
        CREATE TABLE IF NOT EXISTS dim_device (
            asset_tag                   VARCHAR(20)     PRIMARY KEY,
            serial_number               VARCHAR(50)     NOT NULL,
            device_type                 VARCHAR(20)     NOT NULL,
            make                        VARCHAR(50)     NOT NULL,
            model                       VARCHAR(100)    NOT NULL,
            department                  VARCHAR(100)    NOT NULL,
            assigned_user               VARCHAR(100),
            location                    VARCHAR(100),
            status                      VARCHAR(20)     NOT NULL,
            purchase_date               DATE            NOT NULL,
            purchase_cost               NUMERIC(10,2)   NOT NULL,
            useful_life_years           INTEGER         NOT NULL,
            end_of_life_date            DATE            NOT NULL,
            days_to_eol                 INTEGER,
            eol_risk_tier               VARCHAR(20),
            current_book_value          NUMERIC(10,2),
            replacement_budget_flag     BOOLEAN,
            estimated_replacement_cost  NUMERIC(10,2),
            budget_exposure             NUMERIC(10,2),
            load_timestamp              TIMESTAMP,
            data_source                 VARCHAR(100),
            pipeline_version            VARCHAR(20),
            dq_passed                   BOOLEAN
        );
    """

    create_eol_summary = """
        CREATE TABLE IF NOT EXISTS fact_eol_summary (
            summary_id          SERIAL          PRIMARY KEY,
            run_date            DATE            NOT NULL,
            total_devices       INTEGER,
            expired_count       INTEGER,
            critical_count      INTEGER,
            warning_count       INTEGER,
            healthy_count       INTEGER,
            total_exposure      NUMERIC(12,2),
            flagged_for_replace INTEGER,
            load_timestamp      TIMESTAMP
        );
    """

    with engine.connect() as conn:
        conn.execute(text(create_dim_device))
        conn.execute(text(create_eol_summary))
        conn.commit()

    print("  ✅ Tables ready")


# ── Load Device Data ──────────────────────────────────

def load_devices(df: pd.DataFrame, engine) -> int:
    """
    Load device records into dim_device using upsert.
    If asset_tag already exists, update all fields.
    Returns number of records loaded.
    """
    print(f"  📤 Loading {len(df)} records into dim_device...")

    # Convert date columns to string for SQLAlchemy compatibility
    df = df.copy()
    df["purchase_date"]    = df["purchase_date"].astype(str)
    df["end_of_life_date"] = df["end_of_life_date"].astype(str)

    # Upsert using PostgreSQL ON CONFLICT
    upsert_sql = """
        INSERT INTO dim_device (
            asset_tag, serial_number, device_type, make, model,
            department, assigned_user, location, status,
            purchase_date, purchase_cost, useful_life_years,
            end_of_life_date, days_to_eol, eol_risk_tier,
            current_book_value, replacement_budget_flag,
            estimated_replacement_cost, budget_exposure,
            load_timestamp, data_source, pipeline_version, dq_passed
        ) VALUES (
            :asset_tag, :serial_number, :device_type, :make, :model,
            :department, :assigned_user, :location, :status,
            :purchase_date, :purchase_cost, :useful_life_years,
            :end_of_life_date, :days_to_eol, :eol_risk_tier,
            :current_book_value, :replacement_budget_flag,
            :estimated_replacement_cost, :budget_exposure,
            :load_timestamp, :data_source, :pipeline_version, :dq_passed
        )
        ON CONFLICT (asset_tag) DO UPDATE SET
            serial_number              = EXCLUDED.serial_number,
            device_type                = EXCLUDED.device_type,
            make                       = EXCLUDED.make,
            model                      = EXCLUDED.model,
            department                 = EXCLUDED.department,
            assigned_user              = EXCLUDED.assigned_user,
            location                   = EXCLUDED.location,
            status                     = EXCLUDED.status,
            purchase_date              = EXCLUDED.purchase_date,
            purchase_cost              = EXCLUDED.purchase_cost,
            useful_life_years          = EXCLUDED.useful_life_years,
            end_of_life_date           = EXCLUDED.end_of_life_date,
            days_to_eol                = EXCLUDED.days_to_eol,
            eol_risk_tier              = EXCLUDED.eol_risk_tier,
            current_book_value         = EXCLUDED.current_book_value,
            replacement_budget_flag    = EXCLUDED.replacement_budget_flag,
            estimated_replacement_cost = EXCLUDED.estimated_replacement_cost,
            budget_exposure            = EXCLUDED.budget_exposure,
            load_timestamp             = EXCLUDED.load_timestamp,
            pipeline_version           = EXCLUDED.pipeline_version,
            dq_passed                  = EXCLUDED.dq_passed;
    """

    records = df.to_dict(orient="records")

    with engine.connect() as conn:
        for record in records:
            conn.execute(text(upsert_sql), record)
        conn.commit()

    print(f"  ✅ Successfully loaded {len(df)} records into dim_device")
    return len(df)


# ── Load EOL Summary ──────────────────────────────────

def load_eol_summary(df: pd.DataFrame, engine) -> None:
    """
    Load a summary record into fact_eol_summary.
    One row per pipeline run — tracks trends over time.
    """
    print("  📤 Loading EOL summary into fact_eol_summary...")

    summary = {
        "run_date":            datetime.now().date().isoformat(),
        "total_devices":       len(df),
        "expired_count":       int((df["eol_risk_tier"] == "Expired").sum()),
        "critical_count":      int((df["eol_risk_tier"] == "Critical").sum()),
        "warning_count":       int((df["eol_risk_tier"] == "Warning").sum()),
        "healthy_count":       int((df["eol_risk_tier"] == "Healthy").sum()),
        "total_exposure":      float(df["budget_exposure"].sum()),
        "flagged_for_replace": int(df["replacement_budget_flag"].sum()),
        "load_timestamp":      datetime.now().isoformat()
    }

    insert_sql = """
        INSERT INTO fact_eol_summary (
            run_date, total_devices, expired_count, critical_count,
            warning_count, healthy_count, total_exposure,
            flagged_for_replace, load_timestamp
        ) VALUES (
            :run_date, :total_devices, :expired_count, :critical_count,
            :warning_count, :healthy_count, :total_exposure,
            :flagged_for_replace, :load_timestamp
        );
    """

    with engine.connect() as conn:
        conn.execute(text(insert_sql), summary)
        conn.commit()

    print("  ✅ EOL summary loaded")


# ── Verify Load ───────────────────────────────────────

def verify_load(engine) -> None:
    """Run quick verification queries after loading."""
    print("\n  🔍 Verifying load...")

    queries = {
        "Total devices in DB":     "SELECT COUNT(*) FROM dim_device",
        "EOL Risk breakdown": """
            SELECT eol_risk_tier, COUNT(*) as count
            FROM dim_device
            GROUP BY eol_risk_tier
            ORDER BY count DESC
        """,
        "Total budget exposure": """
            SELECT SUM(budget_exposure) as total_exposure
            FROM dim_device
            WHERE replacement_budget_flag = true
        """
    }

    with engine.connect() as conn:
        for label, sql in queries.items():
            result = conn.execute(text(sql))
            rows   = result.fetchall()
            print(f"\n     {label}:")
            for row in rows:
                print(f"       {list(row)}")


# ── Main Load Function ────────────────────────────────

def run_load() -> None:
    """
    Main load function called by the pipeline.
    Reads from warehouse CSV and loads into RDS PostgreSQL.
    """
    print("\n" + "=" * 55)
    print("  ETL Phase 3 — Load")
    print("=" * 55)

    # Read from warehouse
    warehouse_path = os.path.join(
        "data", "warehouse", "assets", "devices_warehouse.csv"
    )

    if not os.path.exists(warehouse_path):
        raise FileNotFoundError(
            f"Warehouse file not found: {warehouse_path}\n"
            f"Please run transform.py first."
        )

    print(f"  📂 Reading from warehouse: {warehouse_path}")
    df = pd.read_csv(warehouse_path)
    print(f"  ✅ Loaded {len(df)} records")

    # Connect to database
    print("  🔌 Connecting to RDS PostgreSQL...")
    engine = get_db_engine()
    print("  ✅ Connected")

    # Create tables
    create_tables(engine)

    # Load data
    load_devices(df, engine)
    load_eol_summary(df, engine)

    # Verify
    verify_load(engine)

    print("\n" + "=" * 55)
    print("  ✅ ETL Load phase complete!")
    print("=" * 55)


if __name__ == "__main__":
    run_load()