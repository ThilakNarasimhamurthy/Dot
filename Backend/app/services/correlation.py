"""
Correlation service for linking traffic, transit, and air quality data
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.database import get_database

logger = logging.getLogger(__name__)


class CorrelationService:
    """Service for correlating traffic, transit delays, and air quality"""
    
    def __init__(self):
        self.db = get_database()
        # Distance threshold for "nearby" (in degrees, roughly 1km = 0.01 degrees)
        self.nearby_threshold = 0.01
    
    async def find_nearby_air_quality(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        time_window_minutes: int = 15
    ) -> Optional[float]:
        """
        Find nearby PM2.5 reading for a given location and time
        
        Args:
            latitude: Segment latitude
            longitude: Segment longitude
            timestamp: Timestamp to match
            time_window_minutes: Time window for matching readings
        
        Returns:
            PM2.5 value or None if not found
        """
        try:
            time_start = timestamp - timedelta(minutes=time_window_minutes)
            time_end = timestamp + timedelta(minutes=time_window_minutes)
            
            # Find air quality readings within geographic and temporal proximity
            readings = await self.db.raw_air_quality.find({
                "latitude": {
                    "$gte": latitude - self.nearby_threshold,
                    "$lte": latitude + self.nearby_threshold
                },
                "longitude": {
                    "$gte": longitude - self.nearby_threshold,
                    "$lte": longitude + self.nearby_threshold
                },
                "timestamp": {
                    "$gte": time_start,
                    "$lte": time_end
                },
                "pm25": {"$exists": True, "$ne": None}
            }).sort("timestamp", -1).limit(5).to_list(length=5)
            
            if readings:
                # Use average of nearby readings
                pm25_values = [r.get("pm25", 0) for r in readings if r.get("pm25")]
                if pm25_values:
                    avg_pm25 = sum(pm25_values) / len(pm25_values)
                    logger.debug(f"Found nearby PM2.5: {avg_pm25:.2f} for lat={latitude}, lon={longitude}")
                    return avg_pm25
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding nearby air quality: {e}")
            return None
    
    async def check_transit_delays_nearby(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        time_window_minutes: int = 15
    ) -> bool:
        """
        Check if there are transit delays nearby that might affect traffic
        
        Args:
            latitude: Segment latitude
            longitude: Segment longitude
            timestamp: Timestamp to check
            time_window_minutes: Time window for checking delays
        
        Returns:
            True if significant transit delays found nearby
        """
        try:
            time_start = timestamp - timedelta(minutes=time_window_minutes)
            time_end = timestamp + timedelta(minutes=time_window_minutes)
            
            # Find transit delays within geographic and temporal proximity
            # Consider delays > 5 minutes as significant
            delayed_trips = await self.db.raw_transit_mta.find({
                "latitude": {
                    "$gte": latitude - self.nearby_threshold * 2,  # Wider radius for transit
                    "$lte": latitude + self.nearby_threshold * 2
                },
                "longitude": {
                    "$gte": longitude - self.nearby_threshold * 2,
                    "$lte": longitude + self.nearby_threshold * 2
                },
                "timestamp": {
                    "$gte": time_start,
                    "$lte": time_end
                },
                "delay_seconds": {"$gt": 300}  # > 5 minutes
            }).limit(3).to_list(length=3)
            
            has_delays = len(delayed_trips) > 0
            
            if has_delays:
                logger.debug(f"Found {len(delayed_trips)} transit delays nearby")
            
            return has_delays
            
        except Exception as e:
            logger.error(f"Error checking transit delays: {e}")
            return False
    
    def calculate_traffic_pollution_risk(
        self,
        congestion_index: float,
        pm25: Optional[float]
    ) -> str:
        """
        Calculate traffic pollution risk level based on congestion and PM2.5
        
        Args:
            congestion_index: Normalized congestion (0-1)
            pm25: PM2.5 reading (optional)
        
        Returns:
            Risk level: "Low" | "Medium" | "High"
        """
        # Base risk on congestion
        if congestion_index < 0.3:
            base_risk = "Low"
        elif congestion_index < 0.6:
            base_risk = "Medium"
        else:
            base_risk = "High"
        
        # Adjust based on PM2.5 if available
        if pm25 is not None:
            # PM2.5 thresholds (μg/m³)
            # Good: < 12, Moderate: 12-35, Unhealthy: > 35
            if pm25 > 35:
                # High PM2.5 overrides to High risk
                return "High"
            elif pm25 > 12 and base_risk == "Low":
                # Moderate PM2.5 upgrades Low to Medium
                return "Medium"
        
        return base_risk
    
    async def correlate_historical_patterns(
        self,
        segment_id: str,
        current_congestion: float,
        current_pm25: Optional[float]
    ) -> Dict:
        """
        Analyze historical correlation between traffic and pollution for a segment
        
        Args:
            segment_id: Segment identifier
            current_congestion: Current congestion index
            current_pm25: Current PM2.5 reading
        
        Returns:
            Dictionary with correlation insights
        """
        try:
            # Get historical data for this segment (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            historical = await self.db.segments_state.find({
                "segment_id": segment_id,
                "timestamp_bucket": {"$gte": week_ago},
                "pm25_nearby": {"$exists": True, "$ne": None}
            }).to_list(length=100)
            
            if len(historical) < 10:
                return {
                    "correlation_available": False,
                    "message": "Insufficient historical data"
                }
            
            # Simple correlation: compare congestion vs PM2.5
            congestion_values = [h.get("congestion_index", 0) for h in historical]
            pm25_values = [h.get("pm25_nearby", 0) for h in historical]
            
            avg_congestion = sum(congestion_values) / len(congestion_values)
            avg_pm25 = sum(pm25_values) / len(pm25_values)
            
            # Check if current values are above average
            congestion_above_avg = current_congestion > avg_congestion * 1.1
            pm25_above_avg = current_pm25 and current_pm25 > avg_pm25 * 1.1
            
            return {
                "correlation_available": True,
                "avg_congestion_7d": round(avg_congestion, 3),
                "avg_pm25_7d": round(avg_pm25, 2),
                "current_congestion_above_avg": congestion_above_avg,
                "current_pm25_above_avg": pm25_above_avg,
                "traffic_pollution_link": congestion_above_avg and pm25_above_avg
            }
            
        except Exception as e:
            logger.error(f"Error correlating historical patterns: {e}")
            return {
                "correlation_available": False,
                "error": str(e)
            }

