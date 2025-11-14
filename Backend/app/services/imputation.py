"""
Data imputation service for filling gaps in traffic data
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.database import get_database

logger = logging.getLogger(__name__)


class ImputationService:
    """Service for imputing missing or invalid data values"""
    
    def __init__(self):
        self.db = get_database()
    
    def clean_speed_value(self, speed: Optional[float], segment_id: str) -> Optional[float]:
        """
        Clean and validate speed value
        
        Args:
            speed: Raw speed value
            segment_id: Segment identifier for context
        
        Returns:
            Cleaned speed value or None if invalid
        """
        if speed is None:
            return None
        
        # Remove negative speeds
        if speed < 0:
            logger.warning(f"Negative speed {speed} for segment {segment_id}, setting to None")
            return None
        
        # Remove impossibly high speeds (>100 mph in NYC)
        if speed > 100:
            logger.warning(f"Impossibly high speed {speed} for segment {segment_id}, capping at 100")
            return 100.0
        
        return speed
    
    async def impute_missing_speed(
        self, 
        segment_id: str, 
        timestamp: datetime,
        current_speed: Optional[float]
    ) -> float:
        """
        Impute missing speed using recent history and nearest segment logic
        
        Args:
            segment_id: Segment identifier
            timestamp: Current timestamp
            current_speed: Current speed (may be None)
        
        Returns:
            Imputed speed value
        """
        if current_speed is not None:
            cleaned = self.clean_speed_value(current_speed, segment_id)
            if cleaned is not None:
                return cleaned
        
        # Try to get recent history (last 30 minutes)
        try:
            recent_cutoff = timestamp - timedelta(minutes=30)
            
            # Query recent segments_state for this segment
            recent_docs = await self.db.segments_state.find({
                "segment_id": segment_id,
                "timestamp_bucket": {"$gte": recent_cutoff}
            }).sort("timestamp_bucket", -1).limit(10).to_list(length=10)
            
            if recent_docs:
                # Use average of recent speeds
                speeds = [doc.get("speed_mph", 0) for doc in recent_docs if doc.get("speed_mph")]
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    logger.info(f"Imputed speed {avg_speed:.2f} for {segment_id} using recent history")
                    return avg_speed
            
            # Fallback: Try to find nearby segments
            # Get segment location first
            segment_doc = await self.db.segments_state.find_one(
                {"segment_id": segment_id},
                sort=[("timestamp_bucket", -1)]
            )
            
            if segment_doc:
                lat = segment_doc.get("latitude", 0)
                lon = segment_doc.get("longitude", 0)
                
                # Find nearby segments (within ~1km, roughly 0.01 degrees)
                nearby_docs = await self.db.segments_state.find({
                    "latitude": {"$gte": lat - 0.01, "$lte": lat + 0.01},
                    "longitude": {"$gte": lon - 0.01, "$lte": lon + 0.01},
                    "timestamp_bucket": {"$gte": recent_cutoff}
                }).sort("timestamp_bucket", -1).limit(5).to_list(length=5)
                
                if nearby_docs:
                    speeds = [doc.get("speed_mph", 0) for doc in nearby_docs if doc.get("speed_mph")]
                    if speeds:
                        avg_speed = sum(speeds) / len(speeds)
                        logger.info(f"Imputed speed {avg_speed:.2f} for {segment_id} using nearby segments")
                        return avg_speed
            
            # Final fallback: Use citywide average (typical NYC traffic speed ~20 mph)
            logger.warning(f"No history found for {segment_id}, using default 20.0 mph")
            return 20.0
            
        except Exception as e:
            logger.error(f"Error imputing speed for {segment_id}: {e}")
            return 20.0  # Safe default
    
    def calculate_congestion_index(self, speed_mph: float, max_speed: float = 50.0) -> float:
        """
        Calculate normalized congestion index (0-1)
        0 = no congestion (high speed)
        1 = severe congestion (low speed)
        
        Args:
            speed_mph: Current speed
            max_speed: Maximum expected speed for normalization
        
        Returns:
            Congestion index between 0 and 1
        """
        if speed_mph >= max_speed:
            return 0.0
        if speed_mph <= 0:
            return 1.0
        
        # Inverse relationship: lower speed = higher congestion
        congestion = 1.0 - (speed_mph / max_speed)
        return max(0.0, min(1.0, congestion))  # Clamp to [0, 1]
    
    def calculate_confidence_score(
        self,
        has_traffic_data: bool,
        has_transit_data: bool,
        has_air_quality: bool,
        speed_quality: str = "good"  # "good" | "imputed" | "missing"
    ) -> float:
        """
        Calculate data confidence score (0-1)
        
        Args:
            has_traffic_data: Whether traffic data is available
            has_transit_data: Whether transit data is available
            has_air_quality: Whether air quality data is available
            speed_quality: Quality of speed data
        
        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        
        # Traffic data is most important (0.6 weight)
        if has_traffic_data:
            score += 0.6
        elif speed_quality == "imputed":
            score += 0.3  # Partial credit for imputed
        
        # Transit data (0.2 weight)
        if has_transit_data:
            score += 0.2
        
        # Air quality (0.2 weight)
        if has_air_quality:
            score += 0.2
        
        # Penalty for missing/imputed speed
        if speed_quality == "imputed":
            score *= 0.8
        elif speed_quality == "missing":
            score *= 0.5
        
        return max(0.0, min(1.0, score))

