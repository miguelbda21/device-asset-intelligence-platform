"""
main.py
-------
FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload

Then visit:
    http://localhost:8000/docs

Author: Dr. Miguel Rodriguez Saldana
Project: Device Asset Intelligence Platform
"""

from fastapi import FastAPI
from api.routers import assets, eol, financials, pipeline

app = FastAPI(
    title       = "Device Asset Intelligence Platform",
    description = """
## 🖥️ Device Asset Intelligence API

Enterprise REST API for computing device lifecycle management.

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /assets | List all devices |
| GET | /assets/{tag} | Single device detail |
| POST | /assets | Add new device |
| GET | /eol/upcoming | Devices approaching EOL |
| GET | /eol/expired | Expired devices still active |
| GET | /eol/summary | EOL by department |
| GET | /financials/summary | Financial KPIs |
| GET | /financials/by-department | Spend by department |
| GET | /financials/exposure | Replacement cost exposure |
| POST | /pipeline/run | Trigger full ETL pipeline |
| GET | /pipeline/status | Last pipeline run stats |

**Author:** Dr. Miguel Rodriguez Saldana, DCS
    """,
    version      = "1.0.0",
    contact      = {"name": "Dr. Miguel Rodriguez Saldana",
                    "url":  "https://github.com/miguelbda21"},
    license_info = {"name": "MIT"}
)

# ── Register all routers ──────────────────────────────
app.include_router(assets.router)
app.include_router(eol.router)
app.include_router(financials.router)
app.include_router(pipeline.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status":  "online",
        "message": "Device Asset Intelligence Platform API",
        "version": "1.0.0",
        "docs":    "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status":   "healthy",
        "api":      "running",
        "database": "connected",
        "version":  "1.0.0"
    }