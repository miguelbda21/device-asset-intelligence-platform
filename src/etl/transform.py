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

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

import os
import pandas as pd
import sys
from datetime import date, datetime
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────
load_dotenv()

# ── Force project root as working directory ───────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Business Logic Functions ──────────────────────────

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
    elif days_to_eol <= 90:
        return "Critical"
    elif days_to_eol <= 180:
        return "Warning"
    else:
        return "Healthy"


def calculate_book_value(
    purchase_cost: float,
    purchase_date: date,
    useful_life_years: int
) -> float:
    """
    Straight-line depreciation.
    Book Value = Cost - (Cost / Useful Life) * Years Owned
    Minimum book value is $0.
    """
    years_owned        = (date.today() - purchase_date).days / 365.25
    annual_depreciation = purchase_cost / useful_life_years
    book_value         = purchase_cost - (annual_depreciation * years_owned)
    return round(max(book_value, 0.0), 2)


def calculate_replacement_cost(
    device_type: str,
    purchase_cost: float
) -> float:
    """
    Estimate replacement cost using inflation factor by device type.
    Assumes ~15% cost increase over typical refresh cycle.
    """
    inflation_factors = {
        "Laptop":  1.15,
        "Desktop": 1.10,
        "Server":  1.20,
        "Mobile":  1.12
    }
    factor = inflation_factors.get(device_type, 1.15)
    return round(purchase_cost * factor, 2)


# ── Data Type Enforcement ─────────────────────────────

def enforce_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast all columns to their correct data types."""
    print("  🔧 Enforcing data types...")

    df["purchase_date"]    = pd.to_datetime(df["purchase_date"]).dt.date
    df["end_of_life_date"] = pd.to_datetime(df["end_of_life_date"]).dt.date
    df["purchase_cost"]    = df["purchase_cost"].astype(float).round(2)
    df["useful_life_years"]= df["useful_life_years"].astype(int)
    df["asset_tag"]        = df["asset_tag"].astype(str).str.strip()
    df["serial_number"]    = df["serial_number"].astype(str).str.strip().str.upper()
    df["device_type"]      = df["device_type"].astype(str).str.strip()
    df["make"]             = df["make"].astype(str).str.strip()
    df["model"]            = df["model"].astype(str).str.strip()
    df["department"]       = df["department"].astype(str).str.strip()
    df["assigned_user"]    = df["assigned_user"].astype(str).str.strip()
    df["location"]         = df["location"].astype(str).str.strip()
    df["status"]           = df["status"].astype(str).str.strip()

    return df


# ── Recalculate Business Fields ───────────────────────

def recalculate_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalculate all derived fields using today's date.
    This ensures accuracy regardless of when data was generated.
    """
    print("  🔧 Recalculating EOL and financial fields...")

    today = date.today()

    # Recalculate days to EOL from today
    df["days_to_eol"] = df["end_of_life_date"].apply(
        lambda eol: (eol - today).days
    )

    # Recalculate risk tier based on fresh days_to_eol
    df["eol_risk_tier"] = df["days_to_eol"].apply(
        calculate_eol_risk_tier
    )

    # Recalculate book value using straight-line depreciation
    df["current_book_value"] = df.apply(
        lambda row: calculate_book_value(
            row["purchase_cost"],
            row["purchase_date"],
            row["useful_life_years"]
        ),
        axis=1
    )

    # Recalculate replacement budget flag
    df["replacement_budget_flag"] = df["days_to_eol"] <= 365

    # Add estimated replacement cost
    df["estimated_replacement_cost"] = df.apply(
        lambda row: calculate_replacement_cost(
            row["device_type"],
            row["purchase_cost"]
        ),
        axis=1
    )

    # Add total exposure (replacement cost for flagged devices only)
    df["budget_exposure"] = df.apply(
        lambda row: row["estimated_replacement_cost"]
        if row["replacement_budget_flag"] else 0.0,
        axis=1
    )

    return df


# ── Add Metadata Fields ───────────────────────────────

def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add pipeline metadata columns."""
    print("  🔧 Adding metadata fields...")

    df["load_timestamp"] = datetime.now().isoformat()
    df["data_source"]    = "synthetic_generator_v1"
    df["pipeline_version"] = "1.0.0"

    return df


# ── Data Quality Checks ───────────────────────────────

def run_data_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run basic data quality checks and flag bad records.
    Does NOT drop bad records — flags them for visibility.
    """
    print("  🔍 Running data quality checks...")

    issues = []

    # Check 1 — Null asset tags
    null_tags = df["asset_tag"].isnull().sum()
    if null_tags > 0:
        issues.append(f"⚠️  {null_tags} records with null asset_tag")

    # Check 2 — Duplicate asset tags
    duplicate_tags = df["asset_tag"].duplicated().sum()
    if duplicate_tags > 0:
        issues.append(f"⚠️  {duplicate_tags} duplicate asset_tags found")

    # Check 3 — Negative purchase costs
    negative_costs = (df["purchase_cost"] <= 0).sum()
    if negative_costs > 0:
        issues.append(f"⚠️  {negative_costs} records with invalid purchase_cost")

    # Check 4 — Expired devices still marked Active
    expired_active = (
        (df["eol_risk_tier"] == "Expired") &
        (df["status"] == "Active")
    ).sum()
    if expired_active > 0:
        issues.append(
            f"⚠️  {expired_active} expired devices still marked Active "
            f"(compliance risk!)"
        )

    # Check 5 — Missing departments
    missing_dept = df["department"].isnull().sum()
    if missing_dept > 0:
        issues.append(f"⚠️  {missing_dept} records with missing department")

    # Add data quality flag column
    df["dq_passed"] = True

    if issues:
        print("\n  📋 Data Quality Issues Found:")
        for issue in issues:
            print(f"     {issue}")
    else:
        print("  ✅ All data quality checks passed!")

    return df


# ── Summary Stats ─────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Print a summary of the transformed dataset."""

    print("\n  📊 Transformation Summary:")
    print(f"     Total records      : {len(df)}")
    print(f"     Device types       : {df['device_type'].value_counts().to_dict()}")
    print(f"\n     EOL Risk Breakdown :")

    risk_counts = df["eol_risk_tier"].value_counts()
    for tier, count in risk_counts.items():
        pct = round(count / len(df) * 100, 1)
        print(f"       {tier:<12} : {count:>4} ({pct}%)")

    total_exposure = df["budget_exposure"].sum()
    flagged        = df["replacement_budget_flag"].sum()
    print(f"\n     Devices flagged for replacement : {flagged}")
    print(f"     Total budget exposure           : ${total_exposure:,.2f}")


# ── Save to Warehouse ─────────────────────────────────

def save_to_warehouse(df: pd.DataFrame) -> str:
    """Save transformed data to local warehouse folder."""
    warehouse_dir  = os.path.join("data", "warehouse", "assets")
    os.makedirs(warehouse_dir, exist_ok=True)
    warehouse_path = os.path.join(warehouse_dir, "devices_warehouse.csv")

    df.to_csv(warehouse_path, index=False)
    print(f"\n  💾 Saved to warehouse → {warehouse_path}")

    return warehouse_path


# ── Main Transform Function ───────────────────────────

def run_transform() -> pd.DataFrame:
    """
    Main transform function called by the pipeline.
    Returns the transformed DataFrame for downstream use.
    """
    print("\n" + "=" * 55)
    print("  ETL Phase 2 — Transform")
    print("=" * 55)

    # Read from staging
    staged_path = os.path.join(
        "data", "staging", "assets", "devices_staged.csv"
    )

    if not os.path.exists(staged_path):
        raise FileNotFoundError(
            f"Staged file not found: {staged_path}\n"
            f"Please run extract.py first."
        )

    print(f"  📂 Reading from staging: {staged_path}")
    df = pd.read_csv(staged_path)
    print(f"  ✅ Loaded {len(df)} records")

    # Run all transformations
    df = enforce_data_types(df)
    df = recalculate_fields(df)
    df = add_metadata(df)
    df = run_data_quality_checks(df)

    # Print summary
    print_summary(df)

    # Save to warehouse
    save_to_warehouse(df)

    print("\n" + "=" * 55)

    return df


if __name__ == "__main__":
    run_transform()
