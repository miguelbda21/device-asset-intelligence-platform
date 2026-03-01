"""
financials.py
-------------
GET /financials/summary       → Overall financial KPIs
GET /financials/by-department → Spend by department
GET /financials/exposure      → Replacement cost exposure

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any

from api.dependencies import get_db

router = APIRouter(prefix="/financials", tags=["Financials"])


@router.get(
    "/summary",
    summary="Overall financial summary",
    description="High-level financial KPIs across all devices."
)
def get_financial_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    sql = """
        SELECT
            COUNT(*)                                              AS total_devices,
            ROUND(COALESCE(SUM(purchase_cost), 0)::numeric, 2)     AS total_purchase_value,
            ROUND(COALESCE(AVG(purchase_cost), 0)::numeric, 2)     AS avg_purchase_cost,
            ROUND(COALESCE(SUM(current_book_value), 0)::numeric, 2) AS total_book_value,
            ROUND(
                (COALESCE(SUM(purchase_cost), 0) -
                 COALESCE(SUM(current_book_value), 0))::numeric, 2
            )                                                     AS total_depreciation,
            ROUND(COALESCE(SUM(budget_exposure), 0)::numeric, 2)   AS total_budget_exposure,
            COUNT(*) FILTER (WHERE replacement_budget_flag = true) AS flagged_for_replacement
        FROM dim_device
    """
    row = db.execute(text(sql)).mappings().one()
    return dict(row)


@router.get(
    "/by-department",
    summary="Financial breakdown by department",
    description="Purchase value, book value, and exposure per department."
)
def get_by_department(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            department,
            COUNT(*)                                                AS total_devices,
            ROUND(COALESCE(SUM(purchase_cost), 0)::numeric, 2)       AS total_purchase_value,
            ROUND(COALESCE(SUM(current_book_value), 0)::numeric, 2)  AS total_book_value,
            ROUND(COALESCE(SUM(budget_exposure), 0)::numeric, 2)     AS total_exposure,
            COUNT(*) FILTER (WHERE replacement_budget_flag = true)   AS flagged_count
        FROM dim_device
        GROUP BY department
        ORDER BY total_exposure DESC
    """
    rows = db.execute(text(sql)).mappings().all()
    return [dict(r) for r in rows]


@router.get(
    "/exposure",
    summary="Replacement cost exposure",
    description="All devices flagged for replacement with estimated costs."
)
def get_exposure(db: Session = Depends(get_db)) -> Dict[str, Any]:
    sql = """
        SELECT
            asset_tag, device_type, make, model, department,
            end_of_life_date, days_to_eol, eol_risk_tier,
            purchase_cost, current_book_value,
            estimated_replacement_cost, budget_exposure
        FROM dim_device
        WHERE replacement_budget_flag = true
        ORDER BY days_to_eol ASC
    """
    rows = db.execute(text(sql)).mappings().all()
    devices = [dict(r) for r in rows]

    total_exposure = round(
        sum((d.get("budget_exposure") or 0) for d in devices),
        2
    )

    return {
        "total_flagged": len(devices),
        "total_exposure": total_exposure,
        "devices": devices,
    }