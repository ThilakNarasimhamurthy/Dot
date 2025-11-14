"""
MongoDB document models (for reference and type hints)
These represent the structure of documents stored in MongoDB collections
"""
from typing import Optional, List
from datetime import datetime
from typing_extensions import TypedDict


# Raw Data Models
class RawTraffic511(TypedDict, total=False):
    """Raw traffic data from 511NY API"""
    timestamp: datetime
    source: str  # "511ny"
    segment_id: str
    segment_name: str
    speed_mph: float
    incident_type: Optional[str]
    incident_description: Optional[str]
    roadwork_flag: bool
    camera_id: Optional[str]
    latitude: float
    longitude: float
    raw_data: dict


class RawTrafficDOT(TypedDict, total=False):
    """Raw traffic data from NYC DOT OpenData"""
    timestamp: datetime
    source: str  # "nyc_dot_opendata"
    segment_id: str
    speed_mph: float
    latitude: float
    longitude: float
    raw_data: dict


class RawTransitMTA(TypedDict, total=False):
    """Raw transit data from MTA GTFS-RT"""
    timestamp: datetime
    source: str  # "mta_gtfs_rt"
    trip_id: str
    route_id: str
    vehicle_id: str
    stop_id: str
    delay_seconds: int
    arrival_time: datetime
    departure_time: datetime
    latitude: float
    longitude: float
    raw_data: dict


class RawAirQuality(TypedDict, total=False):
    """Raw air quality data from DOHMH or AirNow"""
    timestamp: datetime
    source: str  # "dohmn" | "airnow"
    sensor_id: str
    pm25: float
    pm10: Optional[float]
    aqi: Optional[int]
    latitude: float
    longitude: float
    raw_data: dict


# Processed Data Models
class SegmentState(TypedDict, total=False):
    """Processed segment state (5-min buckets)"""
    segment_id: str
    timestamp_bucket: datetime
    speed_mph: float
    congestion_index: float  # 0-1 normalized
    incident_flag: bool
    transit_delay_flag: bool
    pm25_nearby: Optional[float]
    data_confidence_score: float  # 0-1
    latitude: float
    longitude: float
    segment_name: str
    sources: List[str]


class ZoneState(TypedDict, total=False):
    """Aggregated zone state"""
    zone_id: str
    timestamp_bucket: datetime
    avg_speed_mph: float
    avg_congestion_index: float
    avg_pm25: Optional[float]
    traffic_pollution_risk: str  # "Low" | "Medium" | "High"
    segment_count: int
    incident_count: int
    transit_delay_count: int
    bounding_box: dict


# Prediction Models
class PredictedSegment(TypedDict, total=False):
    """Predicted segment state"""
    segment_id: str
    forecast_timestamp: datetime
    target_timestamp: datetime
    forecast_window_minutes: int  # 15 or 30
    predicted_speed_mph: float
    predicted_congestion_index: float
    risk_level: str  # "green" | "yellow" | "red"
    reasoning_tags: List[str]
    confidence_score: float  # 0-1
    model_type: str  # "moving_avg" | "exponential_smoothing" | "gradient_boosting"


# Validation Models
class ValidationMetrics(TypedDict, total=False):
    """Validation metrics"""
    timestamp: datetime
    metric_type: str  # "mae_speed" | "sensor_reliability" | "prediction_accuracy"
    segment_id: Optional[str]
    value: float
    threshold: float
    status: str  # "pass" | "warning" | "fail"
    details: dict

