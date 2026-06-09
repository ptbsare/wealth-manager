"""Polling service API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import get_connection
from app.services.polling_service import polling_service

router = APIRouter(prefix="/api/polling", tags=["polling"])


class PollingConfig(BaseModel):
    interval: int = 300  # seconds


@router.get("/status")
def get_polling_status():
    """Get polling service status."""
    return polling_service.get_status()


@router.post("/config")
def update_polling_config(data: PollingConfig):
    """Update polling configuration."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("polling_interval", str(data.interval))
        )
        conn.commit()
    
    return {"success": True, "interval": data.interval}


@router.get("/prices")
def get_current_prices():
    """Get current stock prices."""
    return polling_service.last_prices


@router.get("/history/{symbol}")
def get_price_history(symbol: str):
    """Get price history for a symbol."""
    history = polling_service.price_history.get(symbol, [])
    return {"symbol": symbol, "history": history}
