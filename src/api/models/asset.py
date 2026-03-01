"""
asset.py
--------
Pydantic models for device asset API requests and responses.

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class AssetBase(BaseModel):
    asset_tag:         str   = Field(..., example="BDA-00001")
    serial_number:     str   = Field(..., example="AB12-3456-XYZ7")
    device_type:       str   = Field(..., example="Laptop")
    make:              str   = Field(..., example="Dell")
    model:             str   = Field(..., example="Latitude 5540")
    department:        str   = Field(..., example="IT Operations")
    assigned_user:     Optional[str] = Field(None, example="John Smith")
    location:          Optional[str] = Field(None, example="Arlington HQ")
    status:            str   = Field(..., example="Active")
    purchase_date:     date  = Field(..., example="2022-01-15")
    purchase_cost:     float = Field(..., example=1850.00)
    useful_life_years: int   = Field(..., example=4)
    end_of_life_date:  date  = Field(..., example="2026-01-15")


class AssetCreate(AssetBase):
    """Model for POST /assets — adding a new device."""
    pass


class AssetResponse(AssetBase):
    """Model for GET responses — includes all calculated fields."""
    days_to_eol:                Optional[int]   = None
    eol_risk_tier:              Optional[str]   = None
    current_book_value:         Optional[float] = None
    replacement_budget_flag:    Optional[bool]  = None
    estimated_replacement_cost: Optional[float] = None
    budget_exposure:            Optional[float] = None
    load_timestamp:             Optional[str]   = None
    pipeline_version:           Optional[str]   = None
    dq_passed:                  Optional[bool]  = None

    class Config:
        from_attributes = True


class AssetSummary(BaseModel):
    """Lightweight model for list responses."""
    asset_tag:        str
    device_type:      str
    make:             str
    model:            str
    department:       str
    status:           str
    end_of_life_date: date
    days_to_eol:      Optional[int]   = None
    eol_risk_tier:    Optional[str]   = None
    purchase_cost:    float
    budget_exposure:  Optional[float] = None

    class Config:
        from_attributes = True


class EOLUpcomingResponse(BaseModel):
    """Response model for EOL upcoming endpoint."""
    asset_tag:                  str
    device_type:                str
    make:                       str
    model:                      str
    department:                 str
    assigned_user:              Optional[str]   = None
    location:                   Optional[str]   = None
    end_of_life_date:           date
    days_to_eol:                int
    eol_risk_tier:              str
    estimated_replacement_cost: Optional[float] = None

    class Config:
        from_attributes = True


class PipelineResponse(BaseModel):
    """Response model for pipeline run endpoint."""
    status:            str
    message:           str
    records_processed: Optional[int]   = None
    duration_seconds:  Optional[float] = None