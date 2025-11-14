"""
Agent 3: Predictive Congestion Agent
Predicts congestion 15-30 minutes ahead using ML models
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.database import get_database
from app.config import settings
from app.ml.prediction_service import PredictionService

logger = logging.getLogger(__name__)


class PredictiveCongestionAgent:
    """Agent responsible for predicting future congestion"""
    
    def __init__(self):
        self.db = get_database()
        self.prediction_service = PredictionService()
        self.forecast_windows = []
        if settings.prediction_window_15min:
            self.forecast_windows.append(15)
        if settings.prediction_window_30min:
            self.forecast_windows.append(30)
    
    async def generate_predictions(self) -> int:
        """
        Generate predictions for all active segments
        
        Returns:
            Number of predictions created
        """
        try:
            # Get recent segments (last 24 hours for demo - more flexible)
            # In production, use last hour, but for demo allow up to 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Get unique segment IDs from recent data
            segments = await self.db.segments_state.find({
                "timestamp_bucket": {"$gte": cutoff_time}
            }).distinct("segment_id")
            
            if not segments:
                logger.warning("No recent segments found for prediction (last 24 hours)")
                # Fallback: try to use any segments if available
                segments = await self.db.segments_state.find({}).distinct("segment_id")
                if not segments:
                    logger.warning("No segments found in database at all")
                    return 0
                logger.info(f"Using {len(segments)} segments from all available data")
            
            predictions_created = 0
            
            for segment_id in segments:
                for window_minutes in self.forecast_windows:
                    # Use ML prediction service
                    prediction = await self.prediction_service.predict_segment(segment_id, window_minutes)
                    if prediction:
                        # Always update with current timestamp to ensure fresh predictions
                        prediction["last_updated"] = datetime.utcnow()
                        # Store prediction - use segment_id + forecast_window as unique key
                        result = await self.db.predicted_segments.update_one(
                            {
                                "segment_id": segment_id,
                                "forecast_window_minutes": window_minutes
                            },
                            {"$set": prediction},
                            upsert=True
                        )
                        if result.upserted_id or result.modified_count > 0:
                            predictions_created += 1
            
            logger.info(f"Generated {predictions_created} predictions")
            return predictions_created
            
        except Exception as e:
            logger.error(f"Error generating predictions: {e}", exc_info=True)
            return 0
    

