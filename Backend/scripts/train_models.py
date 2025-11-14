#!/usr/bin/env python3
"""
Train ML models for congestion prediction
"""
import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection
from app.ml.models import ModelTrainer
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def train_models():
    """Train ML models"""
    print("=" * 80)
    print("TRAINING CONGESTION PREDICTION MODELS")
    print("=" * 80)
    print(f"Model type: {settings.ml_model_type}")
    print(f"Training history: {settings.ml_training_history_days} days")
    print(f"Model path: {settings.ml_model_path}\n")
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        await connect_to_mongo()
        print("✓ Connected\n")
        
        # Train global model
        print("Training global model (all segments)...")
        trainer = ModelTrainer()
        metrics = await trainer.train_global_model()
        
        print(f"\n✓ Global model trained:")
        print(f"  - MAE: {metrics['mae']:.2f} mph")
        print(f"  - RMSE: {metrics['rmse']:.2f} mph")
        print(f"  - R²: {metrics['r2']:.3f}")
        print(f"  - Samples: {metrics['n_samples']}")
        print(f"  - Model saved to: {settings.ml_model_path}\n")
        
        print("=" * 80)
        print("TRAINING COMPLETE")
        print("=" * 80)
        print("\nModels are ready for prediction!")
        print("Run the prediction agent to generate forecasts.\n")
        
    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        print(f"\n❌ Error during training: {e}\n")
    
    finally:
        await close_mongo_connection()
        print("✓ MongoDB connection closed")


if __name__ == "__main__":
    asyncio.run(train_models())

