"""
eol.py
------
GET /eol/upcoming  → Devices expiring within N days
GET /eol/expired   → Devices past EOL still active
GET /eol/summary   → EOL counts by department

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any

from api.dependencies import get_db
from api.models.asset import EOLUpcomingResponse

router = APIRouter(prefix="/eol", tags=["End of Life"])


@router.get(
    "/upcoming",
    response_model=List[EOLUpcomingResponse],
    summary="Devices approaching EOL",
    description="Returns devices expiring within the specified number of days."
)
def get_upcoming_eol(
    days: int = Query(180, ge=1, le=3650, description="Days threshold (90, 180, 365)"),
    department: Optional[str] = Query(None, description="Filter by department"),
    db: Session = Depends(get_db),
):
    sql = """
        SELECT asset_tag, device_type, make, model, department,
               assigned_user, location, end_of_life_date,
               days_to_eol, eol_risk_tier, estimated_replacement_cost
        FROM dim_device
        WHERE days_to_eol BETWEEN 0 AND :days
    """
    params: Dict[str, Any] = {"days": days}

    if department:
        sql += " AND department = :department"
        params["department"] = department

    sql += " ORDER BY days_to_eol ASC"

    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get(
    "/expired",
    summary="Expired devices still active",
    description="Devices past EOL still marked Active — compliance risk."
)
def get_expired_active(db: Session = Depends(get_db)) -> Dict[str, Any]:
    sql = """
        SELECT asset_tag, device_type, make, model, department,
               assigned_user, location, end_of_life_date,
               days_to_eol, status, eol_risk_tier,
               estimated_replacement_cost
        FROM dim_device
        WHERE eol_risk_tier = 'Expired'
          AND status = 'Active'
        ORDER BY days_to_eol ASC
    """
    rows = db.execute(text(sql)).mappings().all()
    devices = [dict(r) for r in rows]

    total = len(devices)
    compliance_risk = "HIGH" if total > 50 else "MEDIUM"

    return {
        "total_expired_active": total,
        "compliance_risk": compliance_risk,
        "devices": devices,
    }


@router.get(
    "/summary",
    summary="EOL summary by department",
    description="EOL risk counts grouped by department."
)
def get_eol_summary(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            department,
            COUNT(*)                                                    AS total,
            SUM(CASE WHEN eol_risk_tier = 'Expired'  THEN 1 ELSE 0 END) AS expired,
            SUM(CASE WHEN eol_risk_tier = 'Critical' THEN 1 ELSE 0 END) AS critical,
            SUM(CASE WHEN eol_risk_tier = 'Warning'  THEN 1 ELSE 0 END) AS warning,
            SUM(CASE WHEN eol_risk_tier = 'Healthy'  THEN 1 ELSE 0 END) AS healthy,
            SUM(COALESCE(budget_exposure, 0))                           AS total_exposure
        FROM dim_device
        GROUP BY department
        ORDER BY expired DESC, critical DESC
    """
    rows = db.execute(text(sql)).mappings().all()
    return [dict(r) for r in rows]