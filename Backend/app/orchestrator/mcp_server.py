"""
MCP Orchestrator Server
Central hub for orchestrating multi-agent workflows:
- Agent 1: Data Ingestion (511NY, NYC DOT, MTA GTFS-RT)
- Agent 2: Cleaning & Correlation (Data Quality, Fusion)
- Agent 3: Prediction Engine (15-30 min Congestion Forecast)
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.agents.agent1_ingestion import IngestionAgent
from app.agents.agent2_cleaning import CleaningCorrelationAgent
from app.agents.agent3_prediction import PredictiveCongestionAgent
from app.services.explanation import ExplanationService
from app.config import settings

logger = logging.getLogger(__name__)


class MCPOrchestratorServer:
    """
    MCP Orchestrator Server - Central control unit for multi-agent system
    
    Responsibilities:
    1. Schedule and run ingestion cycles (Agent 1)
    2. Trigger cleaning & correlation after ingestion (Agent 2)
    3. Run forecast jobs for predictions (Agent 3)
    4. Handle explanation requests
    5. Manage agent lifecycle and coordination
    """
    
    def __init__(self, scheduler: AsyncIOScheduler):
        """
        Initialize MCP Orchestrator Server
        
        Args:
            scheduler: APScheduler instance for managing scheduled tasks
        """
        self.scheduler = scheduler
        self.ingestion_agent = IngestionAgent()
        self.cleaning_agent = CleaningCorrelationAgent()
        self.prediction_agent = PredictiveCongestionAgent()
        self.explanation_service = ExplanationService()
        
        # Track agent execution state
        self.last_ingestion_time: Optional[datetime] = None
        self.last_cleaning_time: Optional[datetime] = None
        self.last_prediction_time: Optional[datetime] = None
        self.ingestion_in_progress = False
        self.cleaning_in_progress = False
        self.prediction_in_progress = False
        
        logger.info("MCP Orchestrator Server initialized")
    
    async def orchestrate_agents(self) -> Dict[str, Any]:
        """
        Main orchestration method - coordinates all agents
        
        Returns:
            Status of orchestration cycle
        """
        logger.info("Starting agent orchestration cycle")
        cycle_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "ingestion": None,
            "cleaning": None,
            "prediction": None,
            "status": "completed"
        }
        
        try:
            # Step 1: Run Ingestion (Agent 1)
            ingestion_result = await self.run_ingestion_cycle()
            cycle_status["ingestion"] = ingestion_result
            
            # Step 2: Run Cleaning & Correlation after ingestion (Agent 2)
            if ingestion_result.get("success", False):
                cleaning_result = await self.run_after_ingestion()
                cycle_status["cleaning"] = cleaning_result
            
            # Step 3: Run Forecast Jobs (Agent 3)
            prediction_result = await self.run_forecast_jobs()
            cycle_status["prediction"] = prediction_result
            
            logger.info("Agent orchestration cycle completed successfully")
            return cycle_status
            
        except Exception as e:
            logger.error(f"Error in orchestration cycle: {e}", exc_info=True)
            cycle_status["status"] = "error"
            cycle_status["error"] = str(e)
            return cycle_status
    
    async def schedule_run_cycles(self):
        """
        Schedule periodic ingestion cycles (Agent 1)
        This is called by the scheduler to run ingestion on a schedule
        """
        if self.ingestion_in_progress:
            logger.warning("Ingestion already in progress, skipping cycle")
            return
        
        try:
            self.ingestion_in_progress = True
            result = await self.run_ingestion_cycle()
            
            # After ingestion completes, trigger cleaning
            if result.get("success", False):
                # Schedule cleaning to run shortly after ingestion
                await asyncio.sleep(5)  # Small delay to ensure data is written
                await self.run_after_ingestion()
            
            self.last_ingestion_time = datetime.utcnow()
            logger.info(f"Ingestion cycle completed: {result.get('records_ingested', 0)} records")
            
        except Exception as e:
            logger.error(f"Error in scheduled ingestion cycle: {e}", exc_info=True)
        finally:
            self.ingestion_in_progress = False
    
    async def run_ingestion_cycle(self) -> Dict[str, Any]:
        """
        Run Agent 1: Data Ingestion
        - 511NY Traffic API
        - NYC DOT Open Data
        - MTA GTFS-RT
        
        Returns:
            Ingestion results with record counts
        """
        logger.info("Running Agent 1: Data Ingestion")
        try:
            results = await self.ingestion_agent.ingest_all_sources()
            
            total_records = sum(results.values())
            logger.info(f"Agent 1 completed: {total_records} total records ingested")
            
            return {
                "success": True,
                "agent": "Agent 1: Ingestion",
                "records_ingested": total_records,
                "breakdown": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Agent 1 ingestion failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": "Agent 1: Ingestion",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_after_ingestion(self) -> Dict[str, Any]:
        """
        Run Agent 2: Cleaning & Correlation
        Triggered after ingestion completes
        - Data Quality Checks
        - Fusion (Traffic + Transit)
        
        Returns:
            Cleaning and correlation results
        """
        if self.cleaning_in_progress:
            logger.warning("Cleaning already in progress, skipping")
            return {"success": False, "reason": "Already in progress"}
        
        logger.info("Running Agent 2: Cleaning & Correlation")
        try:
            self.cleaning_in_progress = True
            results = await self.cleaning_agent.process_raw_data()
            
            self.last_cleaning_time = datetime.utcnow()
            logger.info(f"Agent 2 completed: {results.get('segments_created', 0)} segments, {results.get('zones_created', 0)} zones")
            
            return {
                "success": True,
                "agent": "Agent 2: Cleaning & Correlation",
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Agent 2 cleaning failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": "Agent 2: Cleaning & Correlation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            self.cleaning_in_progress = False
    
    async def run_forecast_jobs(self) -> Dict[str, Any]:
        """
        Run Agent 3: Prediction Engine
        - 15-30 min Congestion Forecast
        
        Returns:
            Prediction results
        """
        if self.prediction_in_progress:
            logger.warning("Prediction already in progress, skipping")
            return {"success": False, "reason": "Already in progress"}
        
        logger.info("Running Agent 3: Prediction Engine (Forecast Jobs)")
        try:
            self.prediction_in_progress = True
            predictions_created = await self.prediction_agent.generate_predictions()
            
            self.last_prediction_time = datetime.utcnow()
            logger.info(f"Agent 3 completed: {predictions_created} predictions created")
            
            return {
                "success": True,
                "agent": "Agent 3: Prediction Engine",
                "predictions_created": predictions_created,
                "forecast_windows": [15, 30],  # 15min and 30min windows
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Agent 3 prediction failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": "Agent 3: Prediction Engine",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            self.prediction_in_progress = False
    
    async def request_explanations(self, limit: int = 5) -> Dict[str, Any]:
        """
        Request AI explanations for traffic hotspots
        
        Args:
            limit: Number of hotspots to explain
            
        Returns:
            Explanation results
        """
        logger.info(f"Requesting explanations for top {limit} hotspots")
        try:
            explanation = await self.explanation_service.explain_hotspots(limit=limit)
            
            return {
                "success": True,
                "explanation": explanation,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Explanation request failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def setup_scheduled_cycles(self):
        """
        Setup scheduled cycles for agents:
        - Agent 1: Scheduled ingestion cycles
        - Agent 2: Runs after ingestion (triggered automatically)
        - Agent 3: Scheduled forecast jobs
        """
        logger.info("Setting up scheduled cycles for MCP Orchestrator")
        
        # Schedule Agent 1: Ingestion cycles
        ingestion_interval = settings.ingestion_interval_traffic
        self.scheduler.add_job(
            self.schedule_run_cycles,
            trigger=IntervalTrigger(seconds=ingestion_interval),
            id="mcp_ingestion_cycle",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
            coalesce=True
        )
        logger.info(f"Scheduled Agent 1 (Ingestion) to run every {ingestion_interval} seconds")
        
        # Schedule Agent 2: Cleaning & Correlation (runs independently, but also triggered after ingestion)
        self.scheduler.add_job(
            self.run_after_ingestion,
            trigger=IntervalTrigger(seconds=120),  # Every 2 minutes
            id="mcp_cleaning_cycle",
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("Scheduled Agent 2 (Cleaning & Correlation) to run every 2 minutes")
        
        # Schedule Agent 3: Forecast jobs
        self.scheduler.add_job(
            self.run_forecast_jobs,
            trigger=IntervalTrigger(seconds=300),  # Every 5 minutes
            id="mcp_forecast_jobs",
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("Scheduled Agent 3 (Prediction Engine) to run every 5 minutes")
        
        logger.info("MCP Orchestrator scheduled cycles configured")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of MCP Orchestrator and all agents
        
        Returns:
            Status information for all agents
        """
        return {
            "orchestrator": "MCP Orchestrator Server",
            "status": "running",
            "agents": {
                "agent1_ingestion": {
                    "name": "Agent 1: Data Ingestion",
                    "sources": ["511NY Traffic API", "NYC DOT Open Data", "MTA GTFS-RT"],
                    "last_run": self.last_ingestion_time.isoformat() if self.last_ingestion_time else None,
                    "in_progress": self.ingestion_in_progress
                },
                "agent2_cleaning": {
                    "name": "Agent 2: Cleaning & Correlation",
                    "functions": ["Data Quality Checks", "Fusion (Traffic + Transit)"],
                    "last_run": self.last_cleaning_time.isoformat() if self.last_cleaning_time else None,
                    "in_progress": self.cleaning_in_progress
                },
                "agent3_prediction": {
                    "name": "Agent 3: Prediction Engine",
                    "forecast": "15-30 min Congestion Forecast",
                    "last_run": self.last_prediction_time.isoformat() if self.last_prediction_time else None,
                    "in_progress": self.prediction_in_progress
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

