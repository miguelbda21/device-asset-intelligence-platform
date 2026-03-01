"""
extract.py
----------
Extracts raw device data from AWS S3 and saves it locally
to the staging folder for transformation.

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

import os
import boto3
import pandas as pd
import sys
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────
load_dotenv()

# ── Force project root as working directory ───────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_s3_client():
    """Create and return an S3 client using env credentials."""
    return boto3.client(
        "s3",
        region_name           = os.getenv("AWS_REGION"),
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    )


def extract_devices_from_s3() -> pd.DataFrame:
    """
    Read devices.csv from S3 raw landing zone
    and return as a pandas DataFrame.
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    s3_key      = "raw/assets/devices.csv"

    print(f"📥 Extracting from S3: s3://{bucket_name}/{s3_key}")

    s3_client = get_s3_client()

    # Download file content directly into pandas
    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=s3_key
    )

    df = pd.read_csv(response["Body"])

    print(f"✅ Extracted {len(df)} records from S3")
    print(f"   Columns : {list(df.columns)}")

    return df


def save_to_staged(df: pd.DataFrame) -> str:
    """
    Save extracted DataFrame to local staging folder.
    This is the input for transform.py.
    """
    staged_dir  = os.path.join("data", "staging", "assets")
    os.makedirs(staged_dir, exist_ok=True)
    staged_path = os.path.join(staged_dir, "devices_staged.csv")

    df.to_csv(staged_path, index=False)
    print(f"💾 Saved to staging → {staged_path}")

    return staged_path


def run_extract() -> pd.DataFrame:
    """
    Main extract function called by the pipeline.
    Returns the raw DataFrame for downstream use.
    """
    print("\n" + "=" * 55)
    print("  ETL Phase 1 — Extract")
    print("=" * 55)

    df = extract_devices_from_s3()
    save_to_staged(df)

    print("=" * 55)
    return df


if __name__ == "__main__":
    run_extract()
