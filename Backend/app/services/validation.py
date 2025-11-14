"""
Validation service for checking prediction accuracy and sensor reliability
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.database import get_database

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating predictions and sensor data"""
    
    def __init__(self):
        self.db = get_database()
    
    async def validate_predictions(self) -> Dict:
        """
        Validate predictions by comparing with actuals
        
        Returns:
            Dictionary with validation metrics
        """
        try:
            # Get predictions from 15-30 minutes ago (should have actuals now)
            time_window_start = datetime.utcnow() - timedelta(minutes=35)
            time_window_end = datetime.utcnow() - timedelta(minutes=10)
            
            predictions = await self.db.predicted_segments.find({
                "forecast_timestamp": {
                    "$gte": time_window_start,
                    "$lte": time_window_end
                }
            }).to_list(length=100)
            
            if not predictions:
                return {
                    "status": "no_data",
                    "message": "No predictions found in validation window"
                }
            
            # Compare predictions with actuals
            mae_speeds = []
            mae_congestion = []
            validated_count = 0
            
            for pred in predictions:
                segment_id = pred.get("segment_id")
                target_time = pred.get("target_timestamp")
                predicted_speed = pred.get("predicted_speed_mph", 0)
                predicted_congestion = pred.get("predicted_congestion_index", 0)
                
                # Find actual state at target time
                actual = await self.db.segments_state.find_one({
                    "segment_id": segment_id,
                    "timestamp_bucket": {
                        "$gte": target_time - timedelta(minutes=5),
                        "$lte": target_time + timedelta(minutes=5)
                    }
                })
                
                if actual:
                    actual_speed = actual.get("speed_mph", 0)
                    actual_congestion = actual.get("congestion_index", 0)
                    
                    # Calculate Mean Absolute Error
                    mae_speeds.append(abs(predicted_speed - actual_speed))
                    mae_congestion.append(abs(predicted_congestion - actual_congestion))
                    validated_count += 1
            
            # Calculate average MAE
            avg_mae_speed = sum(mae_speeds) / len(mae_speeds) if mae_speeds else None
            avg_mae_congestion = sum(mae_congestion) / len(mae_congestion) if mae_congestion else None
            
            # Determine status
            status = "pass"
            if avg_mae_speed and avg_mae_speed > 10:  # > 10 mph error
                status = "warning"
            if avg_mae_speed and avg_mae_speed > 15:
                status = "fail"
            
            # Store validation metrics
            validation_doc = {
                "timestamp": datetime.utcnow(),
                "metric_type": "prediction_accuracy",
                "segment_id": None,
                "value": avg_mae_speed or 0,
                "threshold": 10.0,
                "status": status,
                "details": {
                    "validated_count": validated_count,
                    "mae_speed": avg_mae_speed,
                    "mae_congestion": avg_mae_congestion,
                    "total_predictions": len(predictions)
                }
            }
            
            await self.db.validation_metrics.insert_one(validation_doc)
            
            return {
                "status": status,
                "mae_speed": avg_mae_speed,
                "mae_congestion": avg_mae_congestion,
                "validated_count": validated_count,
                "total_predictions": len(predictions)
            }
            
        except Exception as e:
            logger.error(f"Error validating predictions: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def check_sensor_reliability(self) -> Dict:
        """
        Check sensor reliability by detecting suspicious readings
        
        Returns:
            Dictionary with reliability metrics
        """
        try:
            # Check recent raw data for suspicious patterns
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # Check for constant values (stuck sensors)
            traffic_511 = await self.db.raw_traffic_511.find({
                "timestamp": {"$gte": cutoff_time}
            }).to_list(length=100)
            
            suspicious_count = 0
            total_count = len(traffic_511)
            
            if total_count > 0:
                # Group by segment and check for constant values
                segment_speeds = {}
                for doc in traffic_511:
                    seg_id = doc.get("segment_id")
                    speed = doc.get("speed_mph")
                    if seg_id and speed:
                        if seg_id not in segment_speeds:
                            segment_speeds[seg_id] = []
                        segment_speeds[seg_id].append(speed)
                
                # Check for segments with constant speed (likely stuck sensor)
                for seg_id, speeds in segment_speeds.items():
                    if len(speeds) >= 5:
                        unique_speeds = set(speeds)
                        if len(unique_speeds) == 1:
                            suspicious_count += 1
                            logger.warning(f"Suspicious constant speed detected for segment {seg_id}")
            
            # Calculate reliability score
            reliability_score = 1.0 - (suspicious_count / max(total_count, 1))
            
            status = "pass"
            if reliability_score < 0.9:
                status = "warning"
            if reliability_score < 0.7:
                status = "fail"
            
            # Store validation metrics
            validation_doc = {
                "timestamp": datetime.utcnow(),
                "metric_type": "sensor_reliability",
                "segment_id": None,
                "value": reliability_score,
                "threshold": 0.9,
                "status": status,
                "details": {
                    "suspicious_count": suspicious_count,
                    "total_sensors": total_count,
                    "reliability_score": reliability_score
                }
            }
            
            await self.db.validation_metrics.insert_one(validation_doc)
            
            return {
                "status": status,
                "reliability_score": reliability_score,
                "suspicious_count": suspicious_count,
                "total_sensors": total_count
            }
            
        except Exception as e:
            logger.error(f"Error checking sensor reliability: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_validation_summary(self) -> Dict:
        """
        Get overall validation summary
        
        Returns:
            Dictionary with all validation metrics
        """
        try:
            prediction_validation = await self.validate_predictions()
            sensor_reliability = await self.check_sensor_reliability()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "prediction_accuracy": prediction_validation,
                "sensor_reliability": sensor_reliability,
                "overall_status": self._determine_overall_status(
                    prediction_validation.get("status"),
                    sensor_reliability.get("status")
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _determine_overall_status(self, pred_status: str, sensor_status: str) -> str:
        """Determine overall system status"""
        if pred_status == "fail" or sensor_status == "fail":
            return "fail"
        if pred_status == "warning" or sensor_status == "warning":
            return "warning"
        return "pass"

