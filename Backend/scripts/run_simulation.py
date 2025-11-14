#!/usr/bin/env python3
"""
Test script to run a full simulated cycle: ingestion → cleaning → prediction → validation
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection
from app.agents.agent1_ingestion import IngestionAgent
from app.agents.agent2_cleaning import CleaningCorrelationAgent
from app.agents.agent3_prediction import PredictiveCongestionAgent
from app.services.validation import ValidationService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_simulation():
    """Run a complete simulation cycle"""
    print("=" * 80)
    print("SMART CITY DASHBOARD - SIMULATION CYCLE")
    print("=" * 80)
    print(f"Start time: {datetime.utcnow()}\n")
    
    try:
        # Connect to MongoDB
        print("Step 1: Connecting to MongoDB...")
        await connect_to_mongo()
        print("✓ Connected to MongoDB\n")
        
        # Step 1: Ingestion
        print("Step 2: Running Agent 1 - Data Ingestion...")
        ingestion_agent = IngestionAgent()
        ingestion_results = await ingestion_agent.ingest_all_sources()
        print(f"✓ Ingestion complete:")
        print(f"  - 511NY Traffic: {ingestion_results.get('traffic_511', 0)} records")
        print(f"  - NYC DOT Traffic: {ingestion_results.get('traffic_dot', 0)} records")
        print(f"  - MTA Transit: {ingestion_results.get('transit_mta', 0)} records")
        print(f"  - Air Quality: {ingestion_results.get('air_quality', 0)} records\n")
        
        # Step 2: Cleaning + Correlation
        print("Step 3: Running Agent 2 - Cleaning + Correlation...")
        cleaning_agent = CleaningCorrelationAgent()
        cleaning_results = await cleaning_agent.process_raw_data()
        print(f"✓ Processing complete:")
        print(f"  - Segments created: {cleaning_results.get('segments_created', 0)}")
        print(f"  - Zones created: {cleaning_results.get('zones_created', 0)}\n")
        
        # Step 3: Prediction
        print("Step 4: Running Agent 3 - Predictive Congestion...")
        prediction_agent = PredictiveCongestionAgent()
        predictions_count = await prediction_agent.generate_predictions()
        print(f"✓ Predictions generated: {predictions_count}\n")
        
        # Step 4: Validation
        print("Step 5: Running Validation...")
        validation_service = ValidationService()
        validation_summary = await validation_service.get_validation_summary()
        print(f"✓ Validation complete:")
        print(f"  - Overall status: {validation_summary.get('overall_status', 'unknown')}")
        
        pred_accuracy = validation_summary.get('prediction_accuracy', {})
        if pred_accuracy.get('mae_speed'):
            print(f"  - Prediction MAE (speed): {pred_accuracy['mae_speed']:.2f} mph")
        
        sensor_reliability = validation_summary.get('sensor_reliability', {})
        if sensor_reliability.get('reliability_score'):
            print(f"  - Sensor reliability: {sensor_reliability['reliability_score']:.2%}\n")
        
        # Summary
        print("=" * 80)
        print("SIMULATION CYCLE COMPLETE")
        print("=" * 80)
        print(f"End time: {datetime.utcnow()}\n")
        
        print("Next steps:")
        print("1. Check MongoDB collections for ingested data")
        print("2. Query API endpoints:")
        print("   - GET http://localhost:8000/api/segments/current")
        print("   - GET http://localhost:8000/api/zones/current")
        print("   - GET http://localhost:8000/api/predictions")
        print("   - GET http://localhost:8000/api/health/validation")
        print("\n")
        
    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)
        print(f"\n❌ Error during simulation: {e}\n")
    
    finally:
        # Close MongoDB connection
        await close_mongo_connection()
        print("✓ MongoDB connection closed")


if __name__ == "__main__":
    asyncio.run(run_simulation())

