"""
pipeline.py
-----------
POST /pipeline/run    → Trigger full ETL pipeline
GET  /pipeline/status → Last pipeline run stats

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.api.dependencies import get_db
from src.api.models.asset import PipelineResponse

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post(
    "/run",
    response_model=PipelineResponse,
    summary="Trigger ETL pipeline",
    description="Runs the full extract → transform → load pipeline."
)
def run_pipeline(db: Session = Depends(get_db)) -> PipelineResponse:
    start_time = time.time()

    try:
        # Import inside function so FastAPI can start even if ETL modules aren't needed at startup
        from src.etl.extract import run_extract
        from src.etl.transform import run_transform
        from src.etl.load import run_load

        run_extract()
        run_transform()
        run_load()

        duration = round(time.time() - start_time, 2)

        row = db.execute(text("SELECT COUNT(*) AS records_processed FROM dim_device")).mappings().one()
        records_processed = int(row["records_processed"])

        return PipelineResponse(
            status="success",
            message="ETL pipeline completed successfully",
            records_processed=records_processed,
            duration_seconds=duration,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.get(
    "/status",
    summary="Last pipeline run status",
    description="Statistics from the most recent pipeline run."
)
def get_pipeline_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    sql = """
        SELECT run_date, total_devices, expired_count,
               critical_count, warning_count, healthy_count,
               total_exposure, flagged_for_replace, load_timestamp
        FROM fact_eol_summary
        ORDER BY load_timestamp DESC
        LIMIT 1
    """
    row = db.execute(text(sql)).mappings().one_or_none()

    if row is None:
        return {"status": "No pipeline runs found"}

    return dict(row)