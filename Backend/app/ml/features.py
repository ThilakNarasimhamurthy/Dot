"""
Feature engineering for congestion prediction
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Engineer features from historical segment data"""
    
    def __init__(self, lookback_windows: List[int] = [1, 3, 6, 12]):
        """
        Initialize feature engineer
        
        Args:
            lookback_windows: Number of 5-minute buckets to look back (e.g., [1, 3, 6, 12] = 5, 15, 30, 60 min)
        """
        self.lookback_windows = lookback_windows
    
    def create_features(self, history: List[Dict], current_time: datetime) -> Optional[Dict]:
        """
        Create feature vector from historical data
        
        Args:
            history: List of historical segment states (sorted by timestamp, newest first)
            current_time: Current timestamp for feature calculation
        
        Returns:
            Feature dictionary or None if insufficient data
        """
        if not history or len(history) < max(self.lookback_windows):
            return None
        
        features = {}
        
        # Extract time-based features
        features.update(self._extract_time_features(current_time))
        
        # Extract historical speed features
        features.update(self._extract_speed_features(history))
        
        # Extract congestion features
        features.update(self._extract_congestion_features(history))
        
        # Extract incident/delay flags
        features.update(self._extract_flag_features(history))
        
        # Extract air quality features
        features.update(self._extract_air_quality_features(history))
        
        # Extract trend features
        features.update(self._extract_trend_features(history))
        
        return features
    
    def _extract_time_features(self, timestamp: datetime) -> Dict:
        """Extract time-based features"""
        hour = timestamp.hour
        day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
        is_weekend = 1 if day_of_week >= 5 else 0
        
        # Rush hour indicators
        morning_rush = 1 if 7 <= hour <= 9 else 0
        evening_rush = 1 if 17 <= hour <= 19 else 0
        midday = 1 if 10 <= hour <= 16 else 0
        night = 1 if hour < 7 or hour > 19 else 0
        
        return {
            "hour": hour,
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "morning_rush": morning_rush,
            "evening_rush": evening_rush,
            "midday": midday,
            "night": night
        }
    
    def _extract_speed_features(self, history: List[Dict]) -> Dict:
        """Extract speed-related features from history"""
        speeds = [h.get("speed_mph", 0) for h in history[:max(self.lookback_windows)]]
        
        features = {}
        
        # Current and recent speeds
        if speeds:
            features["speed_current"] = speeds[0]
            features["speed_avg_3"] = np.mean(speeds[:min(3, len(speeds))])
            features["speed_avg_6"] = np.mean(speeds[:min(6, len(speeds))])
            features["speed_std_6"] = np.std(speeds[:min(6, len(speeds))]) if len(speeds) > 1 else 0
        
        # Speed for each lookback window
        for window in self.lookback_windows:
            if len(speeds) >= window:
                window_speeds = speeds[:window]
                features[f"speed_avg_{window}"] = np.mean(window_speeds)
                features[f"speed_min_{window}"] = np.min(window_speeds)
                features[f"speed_max_{window}"] = np.max(window_speeds)
                if len(window_speeds) > 1:
                    features[f"speed_std_{window}"] = np.std(window_speeds)
                else:
                    features[f"speed_std_{window}"] = 0
        
        # Speed trend (slope)
        if len(speeds) >= 3:
            recent = speeds[:3]
            features["speed_trend"] = (recent[0] - recent[-1]) / len(recent)  # Simple slope
        
        return features
    
    def _extract_congestion_features(self, history: List[Dict]) -> Dict:
        """Extract congestion index features"""
        congestion = [h.get("congestion_index", 0) for h in history[:max(self.lookback_windows)]]
        
        features = {}
        
        if congestion:
            features["congestion_current"] = congestion[0]
            features["congestion_avg_3"] = np.mean(congestion[:min(3, len(congestion))])
            features["congestion_avg_6"] = np.mean(congestion[:min(6, len(congestion))])
        
        # Congestion for each lookback window
        for window in self.lookback_windows:
            if len(congestion) >= window:
                window_congestion = congestion[:window]
                features[f"congestion_avg_{window}"] = np.mean(window_congestion)
                features[f"congestion_max_{window}"] = np.max(window_congestion)
        
        return features
    
    def _extract_flag_features(self, history: List[Dict]) -> Dict:
        """Extract incident and delay flags"""
        recent = history[:max(self.lookback_windows)]
        
        incident_count = sum(1 for h in recent if h.get("incident_flag", False))
        transit_delay_count = sum(1 for h in recent if h.get("transit_delay_flag", False))
        
        return {
            "has_incident": 1 if history[0].get("incident_flag", False) else 0,
            "incident_count_6": min(incident_count, 6),
            "has_transit_delay": 1 if history[0].get("transit_delay_flag", False) else 0,
            "transit_delay_count_6": min(transit_delay_count, 6)
        }
    
    def _extract_air_quality_features(self, history: List[Dict]) -> Dict:
        """Extract air quality features"""
        pm25_values = [h.get("pm25_nearby") for h in history[:6] if h.get("pm25_nearby") is not None]
        
        features = {
            "has_pm25": 1 if pm25_values else 0,
            "pm25_current": pm25_values[0] if pm25_values else 0,
            "pm25_avg": np.mean(pm25_values) if pm25_values else 0
        }
        
        return features
    
    def _extract_trend_features(self, history: List[Dict]) -> Dict:
        """Extract trend and change features"""
        if len(history) < 3:
            return {}
        
        speeds = [h.get("speed_mph", 0) for h in history[:6]]
        congestion = [h.get("congestion_index", 0) for h in history[:6]]
        
        features = {}
        
        if len(speeds) >= 3:
            # Speed change over last 3 periods
            features["speed_change_3"] = speeds[0] - speeds[2]
            # Acceleration (change in change)
            if len(speeds) >= 4:
                features["speed_acceleration"] = (speeds[0] - speeds[1]) - (speeds[1] - speeds[2])
        
        if len(congestion) >= 3:
            # Congestion change
            features["congestion_change_3"] = congestion[0] - congestion[2]
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature names (for model training)"""
        # This should match the features created in create_features
        feature_names = [
            "hour", "hour_sin", "hour_cos", "day_of_week", "is_weekend",
            "morning_rush", "evening_rush", "midday", "night",
            "speed_current", "speed_avg_3", "speed_avg_6", "speed_std_6",
            "speed_trend", "congestion_current", "congestion_avg_3", "congestion_avg_6",
            "has_incident", "incident_count_6", "has_transit_delay", "transit_delay_count_6",
            "has_pm25", "pm25_current", "pm25_avg",
            "speed_change_3", "speed_acceleration", "congestion_change_3"
        ]
        
        # Add lookback window features
        for window in self.lookback_windows:
            feature_names.extend([
                f"speed_avg_{window}", f"speed_min_{window}", f"speed_max_{window}", f"speed_std_{window}",
                f"congestion_avg_{window}", f"congestion_max_{window}"
            ])
        
        return feature_names

