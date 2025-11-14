#!/usr/bin/env python3
"""
Test script for prediction cycle
Tests ML model training and prediction generation
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection
from app.agents.agent2_cleaning import CleaningCorrelationAgent
from app.agents.agent3_prediction import PredictiveCongestionAgent
from app.ml.models import ModelTrainer
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_prediction_cycle():
    """Test complete prediction cycle: cleaning → training → prediction"""
    print("=" * 80)
    print("PREDICTION CYCLE TEST")
    print("=" * 80)
    print(f"Start time: {datetime.utcnow()}\n")
    
    try:
        # Connect to MongoDB
        print("Step 1: Connecting to MongoDB...")
        await connect_to_mongo()
        print("✓ Connected\n")
        
        # Step 1: Check if we have processed data
        from app.database import get_database
        db = get_database()
        
        segments_count = await db.segments_state.count_documents({})
        print(f"Step 2: Checking data availability...")
        print(f"  Segments in database: {segments_count}")
        
        if segments_count < 50:
            print("\n⚠️  WARNING: Insufficient data for training")
            print(f"   Need at least 50 segments, have {segments_count}")
            print("   Run ingestion and cleaning first:\n")
            print("   1. python scripts/test_live_ingestion.py")
            print("   2. python scripts/run_simulation.py (runs cleaning)")
            print("\n   Or wait for scheduled agents to collect more data.\n")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
        
        # Step 2: Run cleaning to ensure fresh data
        print("\nStep 3: Running Cleaning + Correlation Agent...")
        cleaning_agent = CleaningCorrelationAgent()
        cleaning_results = await cleaning_agent.process_raw_data()
        print(f"✓ Processing complete:")
        print(f"  - Segments created/updated: {cleaning_results.get('segments_created', 0)}")
        print(f"  - Zones created/updated: {cleaning_results.get('zones_created', 0)}\n")
        
        # Step 3: Check if models exist, train if needed
        import os
        model_path = settings.ml_model_path
        model_file = os.path.join(model_path, f"{settings.ml_model_type}_global.joblib")
        
        if not os.path.exists(model_file):
            print("Step 4: No trained models found. Training models...")
            print(f"  Model type: {settings.ml_model_type}")
            print(f"  Training history: {settings.ml_training_history_days} days\n")
            
            trainer = ModelTrainer()
            metrics = await trainer.train_global_model()
            
            print(f"\n✓ Model trained:")
            print(f"  - MAE: {metrics['mae']:.2f} mph")
            print(f"  - RMSE: {metrics['rmse']:.2f} mph")
            print(f"  - R²: {metrics['r2']:.3f}")
            print(f"  - Training samples: {metrics['n_samples']}")
            print(f"  - Model saved to: {model_file}\n")
        else:
            print("Step 4: Using existing trained model")
            print(f"  Model file: {model_file}\n")
        
        # Step 4: Generate predictions
        print("Step 5: Generating predictions...")
        prediction_agent = PredictiveCongestionAgent()
        predictions_count = await prediction_agent.generate_predictions()
        print(f"✓ Generated {predictions_count} predictions\n")
        
        # Step 5: Show sample predictions
        if predictions_count > 0:
            print("Step 6: Sample predictions:")
            sample_preds = await db.predicted_segments.find({}).sort("target_timestamp", 1).limit(5).to_list(length=5)
            
            for i, pred in enumerate(sample_preds, 1):
                seg_id = pred.get("segment_id", "Unknown")
                speed = pred.get("predicted_speed_mph", 0)
                congestion = pred.get("predicted_congestion_index", 0)
                risk = pred.get("risk_level", "unknown")
                window = pred.get("forecast_window_minutes", 0)
                
                print(f"\n  {i}. Segment: {seg_id}")
                print(f"     Forecast: {window} min ahead")
                print(f"     Predicted Speed: {speed:.1f} mph")
                print(f"     Predicted Congestion: {congestion:.2f}")
                print(f"     Risk Level: {risk.upper()}")
                print(f"     Tags: {', '.join(pred.get('reasoning_tags', []))}")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ PREDICTION CYCLE TEST COMPLETE")
        print("=" * 80)
        print(f"\n✓ Cleaned and processed data")
        print(f"✓ Models trained/loaded")
        print(f"✓ Generated {predictions_count} predictions")
        print("\nNext steps:")
        print("  1. Check predictions API: http://localhost:8000/api/predictions")
        print("  2. Check explanation: http://localhost:8000/api/explain/hotspots")
        print("  3. View validation: http://localhost:8000/api/health/validation")
        print()
        
    except Exception as e:
        logger.error(f"Prediction cycle test error: {e}", exc_info=True)
        print(f"\n❌ Error during prediction cycle test: {e}\n")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_mongo_connection()
        print("✓ MongoDB connection closed")


if __name__ == "__main__":
    asyncio.run(test_prediction_cycle())

