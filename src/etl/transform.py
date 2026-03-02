"""
transform.py
------------
Transforms staging device data by cleaning, validating,
and enriching with calculated business fields.

Key transformations:
- Enforce correct data types
- Recalculate days_to_eol based on today's date
- Recalculate eol_risk_tier
- Recalculate current_book_value (straight-line depreciation)
- Add load_timestamp
- Flag data quality issues

Also:
- Reads/writes using PROJECT_ROOT so paths never go to src/etl/data by mistake
- Mirrors outputs to S3 (staging + warehouse)

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import date, datetime

import boto3
import pandas as pd
from dotenv import load_dotenv

# ── Load environment variables ─────────────────────────
load_dotenv()

# ── Find project root (folder that contains requirements.txt OR .git) ──
def find_project_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "requirements.txt").exists() or (p / ".git").exists():
            return p
    # fallback (safe-ish): two levels up
    return start.parents[1]

PROJECT_ROOT = find_project_root(Path(__file__).resolve())
SRC_DIR = PROJECT_ROOT / "src"

# If you use src/ layout, add it for imports
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))
else:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── AWS helpers ────────────────────────────────────────
def get_s3_client():
    """Create and return an S3 client using env credentials."""
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def upload_file_to_s3(local_path: Path, s3_key: str) -> None:
    """Upload a local file to S3."""
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("Missing environment variable: S3_BUCKET_NAME")

    local_path = local_path.resolve()
    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found for upload: {local_path}")

    s3 = get_s3_client()
    print(f"☁️ Uploading to S3: s3://{bucket_name}/{s3_key}")
    s3.upload_file(str(local_path), bucket_name, s3_key)
    print("✅ Upload complete")


# ── Business Logic Functions ───────────────────────────
def calculate_eol_risk_tier(days_to_eol: int) -> str:
    """
    Classify device EOL risk based on days remaining.
    Critical : <= 90 days
    Warning  : <= 180 days
    Healthy  : > 180 days
    Expired  : already past EOL
    """
    if days_to_eol < 0:
        return "Expired"
    if days_to_eol <= 90:
        return "Critical"
    if days_to_eol <= 180:
        return "Warning"
    return "Healthy"


def calculate_book_value(purchase_cost: float, purchase_date: date, useful_life_years: int) -> float:
    """
    Straight-line depreciation.
    Book Value = Cost - (Cost / Useful Life) * Years Owned
    Minimum book value is $0.
    """
    years_owned = (date.today() - purchase_date).days / 365.25
    annual_depreciation = purchase_cost / useful_life_years
    book_value = purchase_cost - (annual_depreciation * years_owned)
    return round(max(book_value, 0.0), 2)


def calculate_replacement_cost(device_type: str, purchase_cost: float) -> float:
    """
    Estimate replacement cost using inflation factor by device type.
    Assumes ~15% cost increase over typical refresh cycle.
    """
    inflation_factors = {
        "Laptop": 1.15,
        "Desktop": 1.10,
        "Server": 1.20,
        "Mobile": 1.12,
    }
    factor = inflation_factors.get(device_type, 1.15)
    return round(purchase_cost * factor, 2)


# ── Data Type Enforcement ──────────────────────────────
def enforce_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast all columns to their correct data types."""
    print("  🔧 Enforcing data types...")

    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce").dt.date
    df["end_of_life_date"] = pd.to_datetime(df["end_of_life_date"], errors="coerce").dt.date
    df["purchase_cost"] = pd.to_numeric(df["purchase_cost"], errors="coerce").astype(float).round(2)
    df["useful_life_years"] = pd.to_numeric(df["useful_life_years"], errors="coerce").astype("Int64")

    # Strings
    for col in [
        "asset_tag", "serial_number", "device_type", "make", "model",
        "department", "assigned_user", "location", "status"
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["serial_number"] = df["serial_number"].str.upper()

    return df


# ── Recalculate Business Fields ────────────────────────
def recalculate_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Recalculate all derived fields using today's date."""
    print("  🔧 Recalculating EOL and financial fields...")

    today = date.today()

    df["days_to_eol"] = df["end_of_life_date"].apply(lambda eol: (eol - today).days)
    df["eol_risk_tier"] = df["days_to_eol"].apply(calculate_eol_risk_tier)

    df["current_book_value"] = df.apply(
        lambda row: calculate_book_value(
            float(row["purchase_cost"]),
            row["purchase_date"],
            int(row["useful_life_years"]) if pd.notna(row["useful_life_years"]) else 3,
        ),
        axis=1,
    )

    df["replacement_budget_flag"] = df["days_to_eol"] <= 365

    df["estimated_replacement_cost"] = df.apply(
        lambda row: calculate_replacement_cost(row["device_type"], float(row["purchase_cost"])),
        axis=1,
    )

    df["budget_exposure"] = df.apply(
        lambda row: row["estimated_replacement_cost"] if row["replacement_budget_flag"] else 0.0,
        axis=1,
    )

    return df


# ── Add Metadata Fields ────────────────────────────────
def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add pipeline metadata columns."""
    print("  🔧 Adding metadata fields...")

    df["load_timestamp"] = datetime.now().isoformat()
    df["data_source"] = "synthetic_generator_v1"
    df["pipeline_version"] = "1.0.0"

    return df


# ── Data Quality Checks ────────────────────────────────
def run_data_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Run basic data quality checks and flag issues (does not drop records)."""
    print("  🔍 Running data quality checks...")

    issues = []

    null_tags = df["asset_tag"].isnull().sum()
    if null_tags > 0:
        issues.append(f"⚠️  {null_tags} records with null asset_tag")

    duplicate_tags = df["asset_tag"].duplicated().sum()
    if duplicate_tags > 0:
        issues.append(f"⚠️  {duplicate_tags} duplicate asset_tags found")

    negative_costs = (df["purchase_cost"] <= 0).sum()
    if negative_costs > 0:
        issues.append(f"⚠️  {negative_costs} records with invalid purchase_cost")

    expired_active = ((df["eol_risk_tier"] == "Expired") & (df["status"] == "Active")).sum()
    if expired_active > 0:
        issues.append(f"⚠️  {expired_active} expired devices still marked Active (compliance risk!)")

    missing_dept = df["department"].isnull().sum()
    if missing_dept > 0:
        issues.append(f"⚠️  {missing_dept} records with missing department")

    df["dq_passed"] = True  # you can later set False based on rules if desired

    if issues:
        print("\n  📋 Data Quality Issues Found:")
        for issue in issues:
            print(f"     {issue}")
    else:
        print("  ✅ All data quality checks passed!")

    return df


# ── Summary Stats ──────────────────────────────────────
def print_summary(df: pd.DataFrame) -> None:
    print("\n  📊 Transformation Summary:")
    print(f"     Total records      : {len(df)}")
    print(f"     Device types       : {df['device_type'].value_counts().to_dict()}")

    print(f"\n     EOL Risk Breakdown :")
    risk_counts = df["eol_risk_tier"].value_counts()
    for tier, count in risk_counts.items():
        pct = round(count / len(df) * 100, 1)
        print(f"       {tier:<12} : {count:>4} ({pct}%)")

    total_exposure = df["budget_exposure"].sum()
    flagged = df["replacement_budget_flag"].sum()
    print(f"\n     Devices flagged for replacement : {flagged}")
    print(f"     Total budget exposure           : ${total_exposure:,.2f}")


# ── Save to Warehouse ──────────────────────────────────
def save_to_warehouse(df: pd.DataFrame) -> Path:
    """Save transformed data to local warehouse folder."""
    warehouse_dir = PROJECT_ROOT / "data" / "warehouse" / "assets"
    warehouse_dir.mkdir(parents=True, exist_ok=True)

    warehouse_path = warehouse_dir / "devices_warehouse.csv"
    df.to_csv(warehouse_path, index=False)

    print(f"\n  💾 Saved to warehouse → {warehouse_path}")
    return warehouse_path


# ── Main Transform Function ────────────────────────────
def run_transform() -> pd.DataFrame:
    print("\n" + "=" * 55)
    print("  ETL Phase 2 — Transform")
    print("=" * 55)

    staged_path = PROJECT_ROOT / "data" / "staging" / "assets" / "devices_staged.csv"

    if not staged_path.exists():
        raise FileNotFoundError(
            f"Staged file not found: {staged_path}\n"
            f"Please run extract.py first."
        )

    print(f"  📂 Reading from staging: {staged_path}")
    df = pd.read_csv(staged_path)
    print(f"  ✅ Loaded {len(df)} records")

    df = enforce_data_types(df)
    df = recalculate_fields(df)
    df = add_metadata(df)
    df = run_data_quality_checks(df)

    print_summary(df)

    # Save local warehouse
    warehouse_path = save_to_warehouse(df)

    # Mirror to S3
    # (Optional) mirror staged too, for consistency
    try:
        upload_file_to_s3(staged_path, "staging/assets/devices_staged.csv")
        upload_file_to_s3(warehouse_path, "warehouse/assets/devices_warehouse.csv")
    except Exception as e:
        print(f"⚠️  S3 upload skipped/failed: {e}")

    print("\n" + "=" * 55)
    return df


if __name__ == "__main__":
    run_transform()