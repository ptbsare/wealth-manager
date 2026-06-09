"""API routes for Wealth Manager."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi import status
from pydantic import BaseModel

from app.config import Settings, get_settings, get_settings_cached
from app.database import get_connection
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.services.dividend_service import DividendService
from app.services.email_service import EmailService
from app.services.baostock_service import BaoStockService

router = APIRouter()


def get_services(settings: Settings = Depends(get_settings)):
    """Get all services."""
    bao = BaoStockService(settings)
    dividend_svc = DividendService(settings, bao)
    email_svc = EmailService(settings)
    return {
        "bao": bao,
        "dividend": dividend_svc,
        "email": email_svc,
        "settings": settings,
    }


def get_mcp_token_from_db() -> str:
    """Get MCP token from database."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'mcp_token'"
            ).fetchone()
            if row and row["value"]:
                return row["value"]
    except Exception:
        pass
    return ""


def verify_mcp_token(authorization: str = Header(None)) -> str:
    """Verify MCP authorization token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.replace("Bearer ", "")
    db_token = get_mcp_token_from_db()
    if not db_token:
        # Fallback to settings token
        settings = get_settings()
        db_token = settings.mcp_token
    if token != db_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    return token


# --- Pydantic Models ---

class HoldingCreate(BaseModel):
    symbol: str
    name: str = ""
    quantity: float
    cost_price: float


class HoldingUpdate(BaseModel):
    symbol: str | None = None
    name: str | None = None
    quantity: float | None = None
    cost_price: float | None = None
    current_price: float | None = None


class DividendCreate(BaseModel):
    symbol: str
    dividend_date: str
    dividend_per_share: float
    tax_rate: float = 0
    actual_received: float = 0
    status: str = "expected"
    notes: str = ""


class SettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_use_tls: bool | None = None
    baostock_username: str | None = None
    baostock_password: str | None = None


# --- Holdings Endpoints ---

@router.get("/api/holdings")
def list_holdings(services: dict = Depends(get_services)):
    """List all holdings."""
    holdings = services["dividend"].get_holdings()
    return [h.to_dict() for h in holdings]


@router.post("/api/holdings")
def create_holding(data: HoldingCreate, services: dict = Depends(get_services)):
    """Create a new holding or merge with existing one."""
    holding = services["dividend"].add_holding(
        symbol=data.symbol,
        name=data.name,
        quantity=data.quantity,
        cost_price=data.cost_price,
    )
    return JSONResponse(content=holding.to_dict(), status_code=status.HTTP_201_CREATED)


@router.get("/api/holdings/{holding_id}")
def get_holding(holding_id: int, services: dict = Depends(get_services)):
    """Get a holding by ID."""
    holding = services["dividend"].get_holding(holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding.to_dict()


@router.put("/api/holdings/{holding_id}")
def update_holding(holding_id: int, data: HoldingUpdate, services: dict = Depends(get_services)):
    """Update a holding."""
    update_data = data.model_dump(exclude_unset=True)
    holding = services["dividend"].update_holding(holding_id, **update_data)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding.to_dict()


@router.delete("/api/holdings/{holding_id}")
def delete_holding(holding_id: int, services: dict = Depends(get_services)):
    """Delete a holding."""
    success = services["dividend"].delete_holding(holding_id)
    if not success:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"success": True}


@router.post("/api/holdings/refresh-prices")
def refresh_prices(services: dict = Depends(get_services)):
    """Refresh current prices for all holdings."""
    services["dividend"].update_prices()
    return {"success": True}


# --- Dividends Endpoints ---

@router.get("/api/dividends")
def list_dividends(symbol: str | None = None, services: dict = Depends(get_services)):
    """List all dividends."""
    dividends = services["dividend"].get_dividends(symbol)
    return [d.to_dict() for d in dividends]


@router.post("/api/dividends")
def create_dividend(data: DividendCreate, services: dict = Depends(get_services)):
    """Create a dividend record."""
    dividend = Dividend(
        symbol=data.symbol,
        dividend_date=data.dividend_date,
        dividend_per_share=data.dividend_per_share,
        tax_rate=data.tax_rate,
        actual_received=data.actual_received,
        status=data.status,
        notes=data.notes,
    )
    created = services["dividend"].add_dividend(dividend)
    return created.to_dict()


@router.get("/api/dividends/calendar")
def get_dividend_calendar(services: dict = Depends(get_services)):
    """Get dividend calendar."""
    calendar = services["dividend"].get_dividend_calendar()
    return calendar


@router.get("/api/dividends/stats")
def get_portfolio_stats(services: dict = Depends(get_services)):
    """Get portfolio statistics."""
    stats = services["dividend"].get_portfolio_stats()
    return stats


# --- Settings Endpoints ---

@router.get("/api/settings")
def get_settings_api():
    """Get settings (excluding sensitive values)."""
    # Get token from database
    mcp_token = get_mcp_token_from_db()
    if not mcp_token:
        settings = get_settings()
        mcp_token = settings.mcp_token

    # Get other settings from database
    smtp_settings = {}
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'smtp_%' OR key LIKE 'bao%'"
            ).fetchall()
            for row in rows:
                smtp_settings[row["key"]] = row["value"]
    except Exception:
        pass

    return {
        "mcp_token": mcp_token,
        "smtp_host": smtp_settings.get("smtp_host", ""),
        "smtp_port": int(smtp_settings.get("smtp_port", 587)),
        "smtp_user": smtp_settings.get("smtp_user", ""),
        "smtp_from": smtp_settings.get("smtp_from", ""),
        "smtp_to": smtp_settings.get("smtp_to", ""),
        "smtp_use_tls": smtp_settings.get("smtp_use_tls", "true").lower() == "true",
        "smtp_configured": bool(smtp_settings.get("smtp_host") and smtp_settings.get("smtp_from")),
    }


@router.put("/api/settings")
def update_settings(data: SettingsUpdate):
    """Update settings."""
    update_data = data.model_dump(exclude_unset=True)

    with get_connection() as conn:
        for key, value in update_data.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
        conn.commit()

    # Clear settings cache
    get_settings_cached.cache_clear()

    return {"success": True}


@router.post("/api/settings/test-email")
def test_email(services: dict = Depends(get_services)):
    """Test email configuration."""
    success, message = services["email"].test_configuration()
    if success:
        return {"success": True, "message": message}
    raise HTTPException(status_code=400, detail=message)


# --- MCP Endpoints (for LLM integration) ---

@router.get("/mcp/holdings")
def mcp_get_holdings(
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Get holdings via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    holdings = services["dividend"].get_holdings()
    return {
        "holdings": [h.to_dict() for h in holdings],
        "count": len(holdings),
    }


@router.get("/mcp/dividends")
def mcp_get_dividends(
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Get dividends via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    dividends = services["dividend"].get_dividends()
    return {
        "dividends": [d.to_dict() for d in dividends],
        "count": len(dividends),
    }


@router.get("/mcp/calendar")
def mcp_get_calendar(
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Get dividend calendar via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    calendar = services["dividend"].get_dividend_calendar()
    return {
        "calendar": calendar,
        "count": len(calendar),
    }


@router.get("/mcp/stats")
def mcp_get_stats(
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Get portfolio statistics via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    stats = services["dividend"].get_portfolio_stats()
    return stats


@router.post("/mcp/holdings")
def mcp_create_holding(
    data: HoldingCreate,
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Create a holding via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    holding = services["dividend"].add_holding(
        symbol=data.symbol,
        name=data.name,
        quantity=data.quantity,
        cost_price=data.cost_price,
    )
    return holding.to_dict()


@router.put("/mcp/holdings/{holding_id}")
def mcp_update_holding(
    holding_id: int,
    data: HoldingUpdate,
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Update a holding via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    update_data = data.model_dump(exclude_unset=True)
    holding = services["dividend"].update_holding(holding_id, **update_data)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding.to_dict()


@router.delete("/mcp/holdings/{holding_id}")
def mcp_delete_holding(
    holding_id: int,
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Delete a holding via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    success = services["dividend"].delete_holding(holding_id)
    if not success:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"success": True}


@router.post("/mcp/dividends")
def mcp_create_dividend(
    data: DividendCreate,
    authorization: str = Header(None),
    services: dict = Depends(get_services),
):
    """Create a dividend record via MCP (requires authorization)."""
    verify_mcp_token(authorization)
    dividend = Dividend(
        symbol=data.symbol,
        dividend_date=data.dividend_date,
        dividend_per_share=data.dividend_per_share,
        tax_rate=data.tax_rate,
        actual_received=data.actual_received,
        status=data.status,
        notes=data.notes,
    )
    created = services["dividend"].add_dividend(dividend)
    return created.to_dict()

# Stock search endpoint - uses predefined list for fast response
@router.get("/api/stocks")
def search_stocks(q: str = ""):
    """Search stocks by code or name."""
    # Comprehensive list of popular stocks
    all_stocks = [
        {'code': 'sh.600519', 'name': '贵州茅台'},
        {'code': 'sz.000858', 'name': '五粮液'},
        {'code': 'sh.601318', 'name': '中国平安'},
        {'code': 'sz.000001', 'name': '平安银行'},
        {'code': 'sh.600000', 'name': '浦发银行'},
        {'code': 'sz.002415', 'name': '海康威视'},
        {'code': 'sh.600276', 'name': '恒瑞医药'},
        {'code': 'sz.300750', 'name': '宁德时代'},
        {'code': 'sh.601012', 'name': '隆基绿能'},
        {'code': 'sz.002594', 'name': '比亚迪'},
        {'code': 'sh.601899', 'name': '紫金矿业'},
        {'code': 'sz.002475', 'name': '立讯精密'},
        {'code': 'sh.600900', 'name': '长江电力'},
        {'code': 'sz.300059', 'name': '东方财富'},
        {'code': 'sh.601166', 'name': '兴业银行'},
        {'code': 'sz.000333', 'name': '美的集团'},
        {'code': 'sh.600036', 'name': '招商银行'},
        {'code': 'sz.002714', 'name': '牧原股份'},
        {'code': 'sh.600585', 'name': '海螺水泥'},
        {'code': 'sz.002352', 'name': '顺丰控股'},
        {'code': 'sh.600809', 'name': '山西汾酒'},
        {'code': 'sz.002371', 'name': '北方华创'},
        {'code': 'sh.600050', 'name': '中国联通'},
        {'code': 'sz.000568', 'name': '泸州老窖'},
        {'code': 'sh.600938', 'name': '中国海油'},
        {'code': 'sz.002049', 'name': '紫光国微'},
        {'code': 'sh.600223', 'name': '鲁西化工'},
        {'code': 'sz.300124', 'name': '汇川技术'},
        {'code': 'sh.600436', 'name': '片仔癀'},
        {'code': 'sz.300760', 'name': '迈瑞医疗'},
        {'code': 'sh.600547', 'name': '山东黄金'},
        {'code': 'sz.002231', 'name': '奥普光电'},
        {'code': 'sh.600352', 'name': '浙江龙盛'},
        {'code': 'sz.300033', 'name': '同花顺'},
        {'code': 'sh.600104', 'name': '上汽集团'},
        {'code': 'sz.002304', 'name': '洋河股份'},
        {'code': 'sh.600886', 'name': '国投电力'},
        {'code': 'sz.300408', 'name': '三环集团'},
        {'code': 'sh.600016', 'name': '民生银行'},
        {'code': 'sz.000063', 'name': '中兴通讯'},
        {'code': 'sh.600406', 'name': '国电南瑞'},
        {'code': 'sz.300015', 'name': '爱尔眼科'},
        {'code': 'sh.600588', 'name': '用友网络'},
        {'code': 'sz.002459', 'name': '汤姆猫'},
        {'code': 'sh.600028', 'name': '中国石化'},
        {'code': 'sz.000709', 'name': '河钢股份'},
        {'code': 'sh.600893', 'name': '航发动力'},
        {'code': 'sz.300751', 'name': '迈为股份'},
    ]
    
    if q:
        q_lower = q.lower()
        return [s for s in all_stocks if q_lower in s['code'].lower() or q_lower in s['name'].lower()]
    
    return all_stocks

@router.post("/api/dividends/fetch-from-baostock")
def fetch_dividends_from_baostock(services: dict = Depends(get_services)):
    """Auto-fetch dividend data from BaoStock for all holdings."""
    from app.services.baostock_service import BaoStockService
    from app.config import get_settings
    
    settings = get_settings()
    bao = BaoStockService(settings)
    dividend_svc = services["dividend"]
    
    try:
        holdings = dividend_svc.get_holdings()
        count = 0
        
        for holding in holdings:
            try:
                # Get dividend data from BaoStock
                dividends = bao.get_dividend_data(holding.symbol, datetime.now().year)
                
                for div in dividends:
                    # Check if already exists
                    existing = dividend_svc.get_dividends(holding.symbol)
                    plan_date = div.get('dividendPlanDate', '')
                    
                    if plan_date and plan_date != '0':
                        # Check for duplicate
                        is_duplicate = any(
                            d.dividend_date == plan_date and 
                            abs(d.dividend_per_share - div.get('dividCashPsBeforeTax', 0)) < 0.001
                            for d in existing
                        )
                        
                        if not is_duplicate:
                            # Add new dividend record
                            new_dividend = Dividend(
                                symbol=holding.symbol,
                                name=holding.name,
                                dividend_date=plan_date,
                                dividend_per_share=div.get('dividCashPsBeforeTax', 0),
                                tax_rate=0,
                                actual_received=0,
                                status='expected',
                                notes=f'从BaoStock自动获取: {div.get("dividCashStock", "")}'
                            )
                            dividend_svc.add_dividend(new_dividend)
                            count += 1
                            
            except Exception as e:
                logger.warning(f"Failed to fetch dividends for {holding.symbol}: {e}")
                continue
        
        return {"success": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
