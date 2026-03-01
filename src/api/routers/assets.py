"""
assets.py
---------
GET  /assets       → List all assets with filters
GET  /assets/{tag} → Single asset detail
POST /assets       → Add a new device

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date, datetime
from src.api.dependencies import get_db
from src.api.models.asset import AssetSummary, AssetResponse, AssetCreate

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get(
    "/",
    response_model=List[AssetSummary],
    summary="Get all assets",
    description="Returns device records with optional filters."
)
def get_assets(
    device_type:   Optional[str] = Query(None, example="Laptop"),
    department:    Optional[str] = Query(None, example="IT Operations"),
    eol_risk_tier: Optional[str] = Query(None, example="Critical"),
    status:        Optional[str] = Query(None, example="Active"),
    limit:         int           = Query(100, le=500),
    offset:        int           = Query(0),
    db:            Session       = Depends(get_db)
):
    sql    = "SELECT * FROM dim_device WHERE 1=1"
    params = {}

    if device_type:
        sql += " AND device_type = :device_type"
        params["device_type"] = device_type

    if department:
        sql += " AND department = :department"
        params["department"] = department

    if eol_risk_tier:
        sql += " AND eol_risk_tier = :eol_risk_tier"
        params["eol_risk_tier"] = eol_risk_tier

    if status:
        sql += " AND status = :status"
        params["status"] = status

    sql += " ORDER BY days_to_eol ASC LIMIT :limit OFFSET :offset"
    params["limit"]  = limit
    params["offset"] = offset

    result = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in result]


@router.get(
    "/{asset_tag}",
    response_model=AssetResponse,
    summary="Get single asset",
    description="Returns full detail for one device by asset_tag."
)
def get_asset(asset_tag: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM dim_device WHERE asset_tag = :tag"),
        {"tag": asset_tag}
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_tag}' not found")

    return dict(row)


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=201,
    summary="Add new asset",
    description="Adds a new device record — simulates CMDB/SCCM integration."
)
def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    today         = date.today()
    days_to_eol   = (asset.end_of_life_date - today).days
    eol_risk_tier = (
        "Expired"  if days_to_eol < 0   else
        "Critical" if days_to_eol <= 90  else
        "Warning"  if days_to_eol <= 180 else
        "Healthy"
    )

    inflation     = {"Laptop": 1.15, "Desktop": 1.10,
                     "Server": 1.20, "Mobile":  1.12}
    factor        = inflation.get(asset.device_type, 1.15)
    est_replace   = round(asset.purchase_cost * factor, 2)
    years_owned   = (today - asset.purchase_date).days / 365.25
    book_value    = round(
        max(asset.purchase_cost -
            (asset.purchase_cost / asset.useful_life_years) * years_owned, 0), 2
    )
    replace_flag  = days_to_eol <= 365
    exposure      = est_replace if replace_flag else 0.0

    sql = """
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
            status         = EXCLUDED.status,
            days_to_eol    = EXCLUDED.days_to_eol,
            eol_risk_tier  = EXCLUDED.eol_risk_tier,
            load_timestamp = EXCLUDED.load_timestamp
        RETURNING *;
    """

    params = {
        **asset.model_dump(),
        "purchase_date":              asset.purchase_date.isoformat(),
        "end_of_life_date":           asset.end_of_life_date.isoformat(),
        "days_to_eol":                days_to_eol,
        "eol_risk_tier":              eol_risk_tier,
        "current_book_value":         book_value,
        "replacement_budget_flag":    replace_flag,
        "estimated_replacement_cost": est_replace,
        "budget_exposure":            exposure,
        "load_timestamp":             datetime.now().isoformat(),
        "data_source":                "api_direct",
        "pipeline_version":           "1.0.0",
        "dq_passed":                  True
    }

    row = db.execute(text(sql), params).mappings().one()
    db.commit()
    return dict(row)