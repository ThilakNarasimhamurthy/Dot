"""
Health check and validation endpoints
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from datetime import datetime
from app.services.validation import ValidationService
from app.models.schemas import ValidationMetrics
from app.agents.agent1_ingestion import IngestionAgent
from app.agents.agent2_cleaning import CleaningCorrelationAgent
from app.agents.agent3_prediction import PredictiveCongestionAgent
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "smartcity_dashboard"
    }


@router.get("/validation")
async def get_validation():
    """
    Get validation metrics (prediction accuracy, sensor reliability)
    
    Returns:
        Validation summary matching ValidationMetrics schema
    """
    try:
        validation_service = ValidationService()
        summary = await validation_service.get_validation_summary()
        
        # Ensure the response matches ValidationMetrics format expected by frontend
        # Extract metrics from nested structure
        pred_accuracy = summary.get("prediction_accuracy", {})
        sensor_reliability = summary.get("sensor_reliability", {})
        
        # Format response to match ValidationMetrics interface
        return {
            "timestamp": summary.get("timestamp", datetime.utcnow().isoformat()),
            "mae_speed": pred_accuracy.get("mae_speed"),
            "sensor_reliability_score": sensor_reliability.get("reliability_score"),
            "prediction_accuracy": pred_accuracy.get("accuracy_percent"),
            "status": summary.get("overall_status", "pass"),
            "details": {
                "prediction_accuracy": pred_accuracy,
                "sensor_reliability": sensor_reliability
            }
        }
    except Exception as e:
        logger.error(f"Error getting validation metrics: {e}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "details": {"error": str(e)}
        }


@router.post("/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """
    Trigger a complete data refresh cycle:
    1. Ingest new data from all sources
    2. Process and clean the data
    3. Generate new predictions
    
    This is useful for demo purposes to show real-time updates.
    """
    async def run_refresh_cycle():
        try:
            logger.info("Starting manual refresh cycle...")
            
            # Step 1: Ingest new data
            ingestion_agent = IngestionAgent()
            ingestion_results = await ingestion_agent.ingest_all_sources()
            logger.info(f"Ingestion complete: {ingestion_results}")
            
            # Step 2: Process and clean
            cleaning_agent = CleaningCorrelationAgent()
            cleaning_results = await cleaning_agent.process_raw_data()
            logger.info(f"Cleaning complete: {cleaning_results}")
            
            # Step 3: Generate predictions
            prediction_agent = PredictiveCongestionAgent()
            predictions_count = await prediction_agent.generate_predictions()
            logger.info(f"Predictions generated: {predictions_count}")
            
            logger.info("Refresh cycle complete!")
            
        except Exception as e:
            logger.error(f"Error during refresh cycle: {e}", exc_info=True)
    
    # Run in background so API responds immediately
    background_tasks.add_task(run_refresh_cycle)
    
    return {
        "status": "refresh_started",
        "message": "Data refresh cycle initiated. New data will be available shortly.",
        "steps": [
            "Ingesting data from all sources",
            "Processing and cleaning data",
            "Generating predictions"
        ]
    }

