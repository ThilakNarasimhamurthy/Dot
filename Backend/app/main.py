"""
FastAPI main application
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import connect_to_mongo, close_mongo_connection
from app.config import settings
from app.orchestrator.mcp_server import MCPOrchestratorServer
from app.api.routes import segments, zones, predictions, health, explain

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = AsyncIOScheduler()

# MCP Orchestrator Server instance (initialized in lifespan)
mcp_orchestrator: Optional[MCPOrchestratorServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global mcp_orchestrator
    
    # Startup
    logger.info("Starting Smart City Dashboard...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Initialize MCP Orchestrator Server
    logger.info("Initializing MCP Orchestrator Server...")
    mcp_orchestrator = MCPOrchestratorServer(scheduler)
    
    # Setup scheduled cycles through MCP Orchestrator
    mcp_orchestrator.setup_scheduled_cycles()
    
    # Start scheduler
    scheduler.start()
    logger.info("MCP Orchestrator Server started with scheduled cycles")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    scheduler.shutdown()
    await close_mongo_connection()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Smart City Dashboard API",
    description="NYC DOT Smart City Dashboard - Traffic, Transit, and Air Quality Monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - must be added before routes
# Note: Cannot use "*" with allow_credentials=True, so we list specific origins
# Origins are configured via CORS_ORIGINS environment variable (comma-separated)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(segments.router)
app.include_router(zones.router)
app.include_router(predictions.router)
app.include_router(health.router)
app.include_router(explain.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Smart City Dashboard",
        "version": "1.0.0",
        "status": "running",
        "orchestrator": "MCP Orchestrator Server",
        "endpoints": {
            "segments": "/api/segments/current",
            "zones": "/api/zones/current",
            "predictions": "/api/predictions",
            "health": "/api/health",
            "validation": "/api/health/validation",
            "explain": "/api/explain/hotspots",
            "orchestrator": "/api/orchestrator/status",
            "orchestrate": "/api/orchestrator/orchestrate"
        }
    }


@app.get("/api/orchestrator/status")
async def orchestrator_status():
    """Get MCP Orchestrator Server status"""
    if mcp_orchestrator is None:
        return {
            "status": "not_initialized",
            "error": "MCP Orchestrator Server not initialized"
        }
    return mcp_orchestrator.get_status()


@app.post("/api/orchestrator/orchestrate")
async def trigger_orchestration():
    """Manually trigger agent orchestration cycle"""
    if mcp_orchestrator is None:
        return {
            "status": "error",
            "error": "MCP Orchestrator Server not initialized"
        }
    return await mcp_orchestrator.orchestrate_agents()


@app.post("/api/orchestrator/ingestion")
async def trigger_ingestion():
    """Manually trigger Agent 1: Ingestion"""
    if mcp_orchestrator is None:
        return {
            "status": "error",
            "error": "MCP Orchestrator Server not initialized"
        }
    return await mcp_orchestrator.run_ingestion_cycle()


@app.post("/api/orchestrator/cleaning")
async def trigger_cleaning():
    """Manually trigger Agent 2: Cleaning & Correlation"""
    if mcp_orchestrator is None:
        return {
            "status": "error",
            "error": "MCP Orchestrator Server not initialized"
        }
    return await mcp_orchestrator.run_after_ingestion()


@app.post("/api/orchestrator/forecast")
async def trigger_forecast():
    """Manually trigger Agent 3: Forecast Jobs"""
    if mcp_orchestrator is None:
        return {
            "status": "error",
            "error": "MCP Orchestrator Server not initialized"
        }
    return await mcp_orchestrator.run_forecast_jobs()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

