"""
Explanation Service - Generates natural language explanations from structured data
Works completely offline using templates and rules (no Hugging Face needed)
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.database import get_database

logger = logging.getLogger(__name__)


class ExplanationService:
    """Service for generating natural language explanations"""
    
    def __init__(self):
        self.db = get_database()
    
    async def explain_hotspots(self, limit: int = 5) -> Dict:
        """
        Generate explanation of current traffic hotspots
        
        Args:
            limit: Number of top hotspots to include
        
        Returns:
            Dictionary with explanation text and structured data
        """
        try:
            # Get current segment states
            latest = await self.db.segments_state.find_one(
                {},
                sort=[("timestamp_bucket", -1)]
            )
            
            if not latest:
                return {
                    "explanation": "No current traffic data available.",
                    "status": "no_data"
                }
            
            latest_bucket = latest.get("timestamp_bucket")
            
            if not latest_bucket:
                return {
                    "explanation": "No current traffic data available.",
                    "status": "no_data",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Get top congested segments
            segments = await self.db.segments_state.find({
                "timestamp_bucket": latest_bucket
            }).sort("congestion_index", -1).limit(limit).to_list(length=limit)
            
            if not segments:
                return {
                    "explanation": "No current traffic hotspots detected.",
                    "status": "no_data",
                    "timestamp": datetime.utcnow().isoformat(),
                    "hotspots_count": 0
                }
            
            # Get predictions for these segments
            segment_ids = [s.get("segment_id") for s in segments if s.get("segment_id")]
            
            predictions = []
            if segment_ids:
                predictions = await self.db.predicted_segments.find({
                    "segment_id": {"$in": segment_ids},
                    "target_timestamp": {"$gte": datetime.utcnow()}
                }).sort("target_timestamp", 1).to_list(length=limit * 2)
            
            # Get air quality data
            zones = await self.db.zones_state.find({
                "timestamp_bucket": latest_bucket
            }).to_list(length=10)
            
            # Generate explanation
            try:
                explanation = self._generate_explanation(segments, predictions, zones)
            except Exception as e:
                logger.error(f"Error generating explanation: {e}", exc_info=True)
                explanation = f"Traffic monitoring is active. Currently tracking {len(segments)} locations with {len(predictions)} active predictions."
            
            # Return simplified response (don't include full data to avoid serialization issues)
            return {
                "explanation": explanation,
                "timestamp": datetime.utcnow().isoformat(),
                "hotspots_count": len(segments),
                "predictions_count": len(predictions),
                "zones_count": len(zones)
            }
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}", exc_info=True)
            return {
                "explanation": "Unable to generate explanation due to an error.",
                "status": "error",
                "error": str(e)
            }
    
    def _generate_explanation(
        self,
        segments: List[Dict],
        predictions: List[Dict],
        zones: List[Dict]
    ) -> str:
        """Generate natural language explanation from structured data"""
        
        if not segments:
            return "No traffic hotspots detected at this time."
        
        explanation_parts = []
        
        # Introduction
        explanation_parts.append(self._generate_intro(segments))
        
        # Top hotspots
        explanation_parts.append(self._generate_hotspots_section(segments))
        
        # Predictions
        if predictions:
            explanation_parts.append(self._generate_predictions_section(segments, predictions))
        
        # Air quality
        if zones:
            explanation_parts.append(self._generate_air_quality_section(zones))
        
        # Recommendations
        explanation_parts.append(self._generate_recommendations(segments, predictions, zones))
        
        return " ".join(explanation_parts)
    
    def _generate_intro(self, segments: List[Dict]) -> str:
        """Generate introduction sentence"""
        try:
            total = len(segments)
            critical = sum(1 for s in segments if float(s.get("congestion_index", 0)) > 0.7)
            
            if critical > 0:
                return f"Currently monitoring {total} traffic hotspots, with {critical} experiencing severe congestion."
            elif total > 0:
                return f"Currently monitoring {total} traffic hotspots across the city."
            else:
                return "Traffic conditions are generally normal across monitored segments."
        except (ValueError, TypeError) as e:
            logger.warning(f"Error generating intro: {e}")
            return f"Currently monitoring {len(segments)} traffic locations."
    
    def _generate_hotspots_section(self, segments: List[Dict]) -> str:
        """Generate section describing top hotspots"""
        if not segments:
            return ""
        
        parts = []
        parts.append("Top congestion areas:")
        
        for i, seg in enumerate(segments[:3], 1):
            try:
                name = seg.get("segment_name") or seg.get("segment_id", "Unknown")
                # Map segment IDs to friendly names
                segment_id = seg.get("segment_id", "")
                if "511_seg_001" in segment_id:
                    name = "FDR Drive (Downtown)"
                elif "511_seg_002" in segment_id:
                    name = "Brooklyn Bridge Approach"
                elif "511_seg_003" in segment_id:
                    name = "Queens Midtown Tunnel"
                elif "dot_seg_001" in segment_id:
                    name = "Manhattan CBD - Broadway"
                elif "dot_seg_002" in segment_id:
                    name = "Times Square Area"
                elif "dot_seg_003" in segment_id:
                    name = "Central Park South"
                
                speed = float(seg.get("speed_mph", 0))
                congestion = float(seg.get("congestion_index", 0))
                incidents = "with active incidents" if seg.get("incident_flag") else ""
                
                # Describe severity
                if congestion > 0.7:
                    severity = "severe congestion"
                elif congestion > 0.5:
                    severity = "moderate congestion"
                else:
                    severity = "light congestion"
                
                parts.append(
                    f"{i}. {name} shows {severity} (speed: {speed:.1f} mph){incidents}."
                )
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Error processing segment {i} for explanation: {e}")
                continue
        
        return " ".join(parts) if parts else ""
    
    def _generate_predictions_section(
        self,
        segments: List[Dict],
        predictions: List[Dict]
    ) -> str:
        """Generate section about future predictions"""
        if not predictions:
            return ""
        
        # Group predictions by segment
        pred_by_segment = {}
        for pred in predictions:
            seg_id = pred.get("segment_id")
            if seg_id not in pred_by_segment:
                pred_by_segment[seg_id] = []
            pred_by_segment[seg_id].append(pred)
        
        parts = []
        parts.append("Looking ahead:")
        
        # Map segment IDs to friendly names
        def get_friendly_name(seg_id):
            if "511_seg_001" in str(seg_id):
                return "FDR Drive (Downtown)"
            elif "511_seg_002" in str(seg_id):
                return "Brooklyn Bridge Approach"
            elif "511_seg_003" in str(seg_id):
                return "Queens Midtown Tunnel"
            elif "dot_seg_001" in str(seg_id):
                return "Manhattan CBD - Broadway"
            elif "dot_seg_002" in str(seg_id):
                return "Times Square Area"
            elif "dot_seg_003" in str(seg_id):
                return "Central Park South"
            return str(seg_id)
        
        for seg_id, preds in list(pred_by_segment.items())[:3]:
            try:
                name = get_friendly_name(seg_id)
                # Get most recent prediction
                latest_pred = sorted(preds, key=lambda x: x.get("target_timestamp") or datetime.min, reverse=True)[0]
                
                risk = latest_pred.get("risk_level", "yellow")
                window = int(latest_pred.get("forecast_window_minutes", 15))
                predicted_speed = float(latest_pred.get("predicted_speed_mph", 0))
                
                if risk == "red":
                    outlook = f"expected to worsen over the next {window} minutes"
                elif risk == "green":
                    outlook = f"expected to improve over the next {window} minutes"
                else:
                    outlook = f"expected to remain similar over the next {window} minutes"
                
                # Get reasoning tags
                tags = latest_pred.get("reasoning_tags", [])
                if not isinstance(tags, list):
                    tags = []
                reasons = []
                if any("rush" in str(tag).lower() for tag in tags):
                    reasons.append("rush hour traffic")
                if any("incident" in str(tag).lower() for tag in tags):
                    reasons.append("active incidents")
                if any("transit" in str(tag).lower() or "delay" in str(tag).lower() for tag in tags):
                    reasons.append("transit delays")
                
                reason_text = f" due to {', '.join(reasons)}" if reasons else ""
                
                parts.append(
                    f"{name} is {outlook} (predicted speed: {predicted_speed:.1f} mph){reason_text}."
                )
            except (ValueError, TypeError, KeyError, IndexError) as e:
                logger.warning(f"Error processing prediction for {seg_id}: {e}")
                continue
        
        return " ".join(parts) if parts else ""
    
    def _generate_air_quality_section(self, zones: List[Dict]) -> str:
        """Generate section about air quality"""
        if not zones:
            return ""
        
        try:
            # Find zones with high pollution risk
            high_risk_zones = [z for z in zones if z.get("traffic_pollution_risk") == "High"]
            avg_pm25 = None
            
            pm25_values = [float(z.get("avg_pm25", 0)) for z in zones if z.get("avg_pm25") is not None]
            if pm25_values:
                avg_pm25 = sum(pm25_values) / len(pm25_values)
            
            parts = []
            
            if high_risk_zones:
                zone_names = [z.get("zone_id", "Unknown").replace("_", " ").title() for z in high_risk_zones[:2]]
                parts.append(
                    f"Air quality concerns: {', '.join(zone_names)} showing elevated pollution risk linked to traffic congestion."
                )
            
            if avg_pm25:
                if avg_pm25 > 35:
                    parts.append(f"Average PM2.5 levels are elevated ({avg_pm25:.1f} μg/m³), indicating air quality impact from traffic.")
                elif avg_pm25 > 12:
                    parts.append(f"Average PM2.5 levels are moderate ({avg_pm25:.1f} μg/m³).")
                else:
                    parts.append(f"Air quality is within acceptable ranges (PM2.5: {avg_pm25:.1f} μg/m³).")
            
            return " ".join(parts) if parts else ""
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Error generating air quality section: {e}")
            return ""
    
    def _generate_recommendations(
        self,
        segments: List[Dict],
        predictions: List[Dict],
        zones: List[Dict]
    ) -> str:
        """Generate actionable recommendations"""
        try:
            recommendations = []
            
            # Check for critical issues
            critical_segments = [s for s in segments if float(s.get("congestion_index", 0)) > 0.7]
            incidents = [s for s in segments if s.get("incident_flag")]
            high_pollution = [z for z in zones if z.get("traffic_pollution_risk") == "High"]
            
            if critical_segments:
                recommendations.append("Consider traffic management interventions for severely congested areas")
            
            if incidents:
                recommendations.append("Monitor and respond to active incidents")
            
            if high_pollution:
                recommendations.append("Review air quality mitigation strategies in high-traffic zones")
            
            # Check predictions
            worsening = [p for p in predictions if p.get("risk_level") == "red"]
            if worsening:
                recommendations.append("Prepare for worsening conditions in predicted hotspots")
            
            if not recommendations:
                recommendations.append("Continue monitoring current conditions")
            
            return f"Recommended actions: {', '.join(recommendations)}."
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Error generating recommendations: {e}")
            return "Recommended actions: Continue monitoring current conditions."

