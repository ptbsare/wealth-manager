"""Main application entry point for Wealth Manager."""

import logging
import traceback
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.database import init_db
from app.api import router
from app.services.polling_service import PollingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create a custom Jinja2 environment without caching
from jinja2 import Environment, FileSystemLoader

_jinja_env = Environment(
    loader=FileSystemLoader("app/templates"),
    auto_reload=False,
    enable_async=False,
    cache_size=0,  # Disable caching to avoid the dict hashing issue
)

# Initialize polling service
polling_service = PollingService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info(f"MCP Token: {settings.mcp_token}")
    
    # Start polling service
    await polling_service.start()
    logger.info("Polling service started")
    
    logger.info("Application started")
    yield
    
    # Shutdown
    await polling_service.stop()
    try:
        from app.services.baostock_service import BaoStockService
        bao = BaoStockService(settings)
        bao.logout()
    except Exception:
        pass


app = FastAPI(
    title="Wealth Manager",
    description="A comprehensive wealth management application",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(router)

# Include notification routes
from app.api.notifications import router as notification_router
app.include_router(notification_router)

# Include polling routes
from app.api.polling import router as polling_router
app.include_router(polling_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page."""
    try:
        # Create a fresh context for each request
        context = {
            "request": request,
            "app_name": str(settings.app_name),
            "mcp_token": str(settings.mcp_token),
        }
        # Use the Jinja2 environment directly
        template = _jinja_env.get_template("index.html")
        content = template.render(**context)
        return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Template error: {e}")
        logger.error(traceback.format_exc())
        # Return a simple HTML response if template fails
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Wealth Manager</title></head>
<body>
<h1>Wealth Manager</h1>
<p>Application is running. Please check the console for errors.</p>
</body>
</html>
""", status_code=500)


def main():
    """Run the application."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
