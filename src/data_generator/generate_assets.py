"""
generate_assets.py
------------------
Generates 500 synthetic computing device records and uploads
them to AWS S3 as the raw landing zone for the ETL pipeline.

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

import os
import random
import boto3
import pandas as pd
from faker import Faker
from datetime import date, timedelta
from dotenv import load_dotenv
import sys

# ── Load environment variables ────────────────────────
load_dotenv()

# ── Force project root as working directory ───────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Initialize Faker ──────────────────────────────────
fake = Faker()
random.seed(42)  # Reproducible results every run

# ── Constants ─────────────────────────────────────────
DEVICE_TYPES = ["Laptop", "Desktop", "Server", "Mobile"]

MAKES = {
    "Laptop":  ["Dell", "HP", "Lenovo", "Apple", "Microsoft"],
    "Desktop": ["Dell", "HP", "Lenovo"],
    "Server":  ["Dell", "HP", "IBM"],
    "Mobile":  ["Apple", "Samsung", "Google"]
}

MODELS = {
    "Dell":      ["Latitude 5540", "OptiPlex 7090", "PowerEdge R750"],
    "HP":        ["EliteBook 840", "ProDesk 600", "ProLiant DL380"],
    "Lenovo":    ["ThinkPad X1 Carbon", "ThinkCentre M90"],
    "Apple":     ["MacBook Pro 14", "iPhone 15 Pro"],
    "Microsoft": ["Surface Pro 9"],
    "IBM":       ["System x3650"],
    "Samsung":   ["Galaxy S24"],
    "Google":    ["Pixel 8"]
}

DEPARTMENTS = [
    "IT Operations",
    "Finance",
    "Human Resources",
    "Clinical Informatics",
    "Revenue Cycle",
    "Cybersecurity",
    "Business Intelligence",
    "Supply Chain"
]

LOCATIONS = [
    "Arlington HQ",
    "Dallas Campus",
    "Fort Worth Campus",
    "Remote",
    "Data Center"
]

STATUSES = ["Active", "Active", "Active", "In-Repair", "Retired"]

# Useful life by device type (years)
USEFUL_LIFE = {
    "Laptop":  4,
    "Desktop": 5,
    "Server":  6,
    "Mobile":  3
}

# Cost ranges by device type (USD)
COST_RANGE = {
    "Laptop":  (800,  2500),
    "Desktop": (600,  1800),
    "Server":  (3000, 12000),
    "Mobile":  (400,  1200)
}


def calculate_eol_risk_tier(days_to_eol: int) -> str:
    """Classify device EOL risk based on days remaining."""
    if days_to_eol <= 90:
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
    years_owned = (date.today() - purchase_date).days / 365.25
    annual_depreciation = purchase_cost / useful_life_years
    book_value = purchase_cost - (annual_depreciation * years_owned)
    return round(max(book_value, 0.0), 2)


def generate_device(asset_number: int) -> dict:
    """Generate a single synthetic device record."""

    # Pick device type and related attributes
    device_type = random.choice(DEVICE_TYPES)
    make        = random.choice(MAKES[device_type])
    model       = random.choice(MODELS.get(make, ["Standard Model"]))
    department  = random.choice(DEPARTMENTS)
    location    = random.choice(LOCATIONS)
    status      = random.choices(
                      STATUSES,
                      weights=[60, 60, 60, 10, 10]
                  )[0]

    # Dates
    useful_life   = USEFUL_LIFE[device_type]
    purchase_date = fake.date_between(
                        start_date="-6y",
                        end_date="today"
                    )
    eol_date      = purchase_date + timedelta(days=useful_life * 365)
    days_to_eol   = (eol_date - date.today()).days

    # Financials
    min_cost, max_cost = COST_RANGE[device_type]
    purchase_cost      = round(random.uniform(min_cost, max_cost), 2)
    book_value         = calculate_book_value(
                             purchase_cost,
                             purchase_date,
                             useful_life
                         )
    replacement_flag = days_to_eol <= 365

    return {
        "asset_tag":               f"BDA-{asset_number:05d}",
        "serial_number":           fake.bothify("??##-####-???#").upper(),
        "device_type":             device_type,
        "make":                    make,
        "model":                   model,
        "department":              department,
        "assigned_user":           fake.name(),
        "location":                location,
        "status":                  status,
        "purchase_date":           purchase_date.isoformat(),
        "purchase_cost":           purchase_cost,
        "useful_life_years":       useful_life,
        "end_of_life_date":        eol_date.isoformat(),
        "days_to_eol":             days_to_eol,
        "eol_risk_tier":           calculate_eol_risk_tier(days_to_eol),
        "current_book_value":      book_value,
        "replacement_budget_flag": replacement_flag
    }


def generate_all_devices(count: int = 500) -> pd.DataFrame:
    """Generate a full dataset of synthetic devices."""
    print(f"🔄 Generating {count} synthetic device records...")
    devices = [generate_device(i + 1) for i in range(count)]
    df = pd.DataFrame(devices)
    print(f"✅ Generated {len(df)} records")
    return df


def save_locally(df: pd.DataFrame) -> str:
    """Save the dataframe to the local raw data folder."""
    output_dir  = os.path.join("data", "raw", "assets")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "devices.csv")
    df.to_csv(output_path, index=False)
    print(f"💾 Saved locally → {output_path}")
    return output_path


def upload_to_s3(local_path: str) -> None:
    """Upload the CSV file to AWS S3 raw landing zone."""
    bucket_name = os.getenv("S3_BUCKET_NAME")
    s3_key      = "raw/assets/devices.csv"

    print(f"☁️  Uploading to S3: s3://{bucket_name}/{s3_key}")

    s3_client = boto3.client(
        "s3",
        region_name           = os.getenv("AWS_REGION"),
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    s3_client.upload_file(local_path, bucket_name, s3_key)
    print(f"✅ Uploaded to S3 successfully!")
    print(f"   Bucket : {bucket_name}")
    print(f"   Key    : {s3_key}")


def main():
    print("=" * 55)
    print("  Device Asset Intelligence Platform")
    print("  Synthetic Data Generator")
    print("=" * 55)

    # 1. Generate
    df = generate_all_devices(500)

    # 2. Preview
    print("\n📊 Sample records (first 3):")
    print(df[["asset_tag", "device_type", "make",
              "end_of_life_date", "eol_risk_tier",
              "purchase_cost"]].head(3).to_string(index=False))

    # 3. Save locally
    local_path = save_locally(df)

    # 4. Upload to S3
    upload_to_s3(local_path)

    print("\n" + "=" * 55)
    print("  ✅ Data generation complete!")
    print("=" * 55)


if __name__ == "__main__":
    main()