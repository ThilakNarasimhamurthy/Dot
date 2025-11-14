"""
Prediction service that uses trained ML models
"""
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from app.database import get_database
from app.ml.models import CongestionPredictor
from app.ml.features import FeatureEngineer
from app.config import settings

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for generating predictions using ML models"""
    
    def __init__(self):
        self.db = get_database()
        self.feature_engineer = FeatureEngineer()
        self.model_cache = {}  # Cache loaded models
    
    def _get_predictor(self, segment_id: str) -> Optional[CongestionPredictor]:
        """Get or load predictor for a segment"""
        # Try segment-specific model first
        predictor = CongestionPredictor(segment_id=segment_id)
        
        try:
            predictor.load_model()
            return predictor
        except FileNotFoundError:
            # Fallback to global model
            logger.debug(f"No segment-specific model for {segment_id}, using global model")
            try:
                global_predictor = CongestionPredictor(segment_id=None)
                global_predictor.load_model()
                return global_predictor
            except FileNotFoundError:
                logger.warning("No trained models found. Train models first.")
                return None
    
    async def predict_segment(
        self,
        segment_id: str,
        forecast_minutes: int = 15
    ) -> Optional[Dict]:
        """
        Predict future state for a segment
        
        Args:
            segment_id: Segment identifier
            forecast_minutes: Minutes ahead to predict (15 or 30)
        
        Returns:
            Prediction dictionary or None if prediction fails
        """
        try:
            # Get recent history for this segment
            # For demo, allow up to 7 days of history (since we have historical data)
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            
            history = await self.db.segments_state.find({
                "segment_id": segment_id,
                "timestamp_bucket": {"$gte": cutoff_time}
            }).sort("timestamp_bucket", -1).limit(20).to_list(length=20)
            
            if len(history) < 3:
                logger.debug(f"Insufficient history for {segment_id}: {len(history)} records (need 3)")
                return None
            
            # Reverse to get oldest first (for feature engineering)
            history = list(reversed(history))
            
            # Get predictor
            predictor = self._get_predictor(segment_id)
            if not predictor:
                return None
            
            # Create features
            target_time = datetime.utcnow() + timedelta(minutes=forecast_minutes)
            features = self.feature_engineer.create_features(history, datetime.utcnow())
            
            if not features:
                return None
            
            # Predict
            predicted_speed, predicted_congestion = predictor.predict(features)
            
            # Determine risk level
            risk_level = self._determine_risk_level(predicted_congestion, predicted_speed)
            
            # Generate reasoning tags
            reasoning_tags = self._generate_reasoning_tags(history, features, predicted_congestion)
            
            # Calculate confidence (based on data quality)
            confidence = min(1.0, len(history) / 20.0)
            
            prediction = {
                "segment_id": segment_id,
                "forecast_timestamp": datetime.utcnow(),
                "target_timestamp": target_time,
                "forecast_window_minutes": forecast_minutes,
                "predicted_speed_mph": predicted_speed,
                "predicted_congestion_index": predicted_congestion,
                "risk_level": risk_level,
                "reasoning_tags": reasoning_tags,
                "confidence_score": confidence,
                "model_type": settings.ml_model_type
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting segment {segment_id}: {e}", exc_info=True)
            return None
    
    def _determine_risk_level(self, congestion_index: float, speed_mph: float) -> str:
        """Determine risk level from predictions"""
        if congestion_index < 0.4 and speed_mph > 20:
            return "green"
        if congestion_index > 0.7 or speed_mph < 10:
            return "red"
        return "yellow"
    
    def _generate_reasoning_tags(
        self,
        history: list,
        features: Dict,
        predicted_congestion: float
    ) -> List[str]:
        """Generate reasoning tags for prediction"""
        tags = []
        
        # Time-based tags
        if features.get("morning_rush"):
            tags.append("morning_rush_hour")
        elif features.get("evening_rush"):
            tags.append("evening_rush_hour")
        elif features.get("midday"):
            tags.append("midday_period")
        else:
            tags.append("off_peak")
        
        # Trend tags
        speed_change = features.get("speed_change_3", 0)
        if speed_change < -5:
            tags.append("speed_declining")
        elif speed_change > 5:
            tags.append("speed_improving")
        else:
            tags.append("speed_stable")
        
        # Incident tags
        if features.get("has_incident"):
            tags.append("active_incident")
        if features.get("has_transit_delay"):
            tags.append("transit_delay_impact")
        
        # Congestion level
        if predicted_congestion > 0.6:
            tags.append("high_congestion_expected")
        elif predicted_congestion < 0.3:
            tags.append("low_congestion_expected")
        
        # Air quality impact
        if features.get("pm25_current", 0) > 35:
            tags.append("high_pollution")
        
        return tags

