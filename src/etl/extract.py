"""
extract.py
----------
Extracts raw device data from AWS S3 and saves it locally
to the staging folder for transformation.

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

import os
import sys
from pathlib import Path

import boto3
import pandas as pd
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────
load_dotenv()


# ── Find project root (folder that contains requirements.txt OR .git) ──
def find_project_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "requirements.txt").exists() or (p / ".git").exists():
            return p
    # fallback: go up 2 levels
    return start.parents[1]


PROJECT_ROOT = find_project_root(Path(__file__).resolve())
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"  # ✅ always points to repo_root/data

# Add /src to imports if you are using src/ layout
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))
else:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_s3_client():
    """Create and return an S3 client using env credentials."""
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def extract_devices_from_s3() -> pd.DataFrame:
    """
    Read devices.csv from S3 raw landing zone
    and return as a pandas DataFrame.
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    s3_key = "raw/assets/devices.csv"

    if not bucket_name:
        raise ValueError("Missing environment variable: S3_BUCKET_NAME")

    print(f"📥 Extracting from S3: s3://{bucket_name}/{s3_key}")

    s3_client = get_s3_client()
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)

    df = pd.read_csv(response["Body"])

    print(f"✅ Extracted {len(df)} records from S3")
    print(f"   Columns : {list(df.columns)}")

    return df


def upload_file_to_s3(local_path: Path, s3_key: str) -> None:
    """Upload a local file to S3."""
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("Missing environment variable: S3_BUCKET_NAME")

    s3_client = get_s3_client()

    print(f"☁️ Uploading to S3: s3://{bucket_name}/{s3_key}")
    s3_client.upload_file(str(local_path), bucket_name, s3_key)
    print("✅ Upload complete")


def save_to_staged(df: pd.DataFrame) -> str:
    """
    Save extracted DataFrame to local staging folder.
    This is the input for transform.py.
    """
    # ✅ Absolute path: <repo_root>/data/staging/assets
    staged_dir = DATA_DIR / "staging" / "assets"
    staged_dir.mkdir(parents=True, exist_ok=True)

    staged_path = staged_dir / "devices_staged.csv"
    df.to_csv(staged_path, index=False)

    print(f"💾 Saved to staging → {staged_path}")

    # ✅ ALSO store staging in S3 (mirror your local folder structure)
    upload_file_to_s3(
        local_path=staged_path,
        s3_key="staging/assets/devices_staged.csv",
    )

    return str(staged_path)


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