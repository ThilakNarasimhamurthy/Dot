"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# Segment State Schemas
class SegmentState(BaseModel):
    """Current state of a traffic segment"""
    segment_id: str
    timestamp_bucket: datetime
    speed_mph: float
    congestion_index: float = Field(ge=0, le=1)
    incident_flag: bool
    transit_delay_flag: bool
    pm25_nearby: Optional[float] = None
    data_confidence_score: float = Field(ge=0, le=1)
    latitude: float
    longitude: float
    segment_name: str
    sources: List[str]
    borough: Optional[str] = None  # "Manhattan" | "Brooklyn" | "Queens" | "Bronx" | "Staten Island"


class ZoneState(BaseModel):
    """Aggregated state of a geographic zone"""
    zone_id: str
    timestamp_bucket: datetime
    avg_speed_mph: float
    avg_congestion_index: float = Field(ge=0, le=1)
    avg_pm25: Optional[float] = None
    traffic_pollution_risk: str  # "Low" | "Medium" | "High"
    segment_count: int
    incident_count: int
    transit_delay_count: int
    borough: Optional[str] = None  # "Manhattan" | "Brooklyn" | "Queens" | "Bronx" | "Staten Island"
    bounding_box: Optional[Dict[str, float]] = None  # {"min_lat": float, "max_lat": float, "min_lon": float, "max_lon": float}


class PredictedSegment(BaseModel):
    """Predicted future state of a segment"""
    segment_id: str
    forecast_timestamp: datetime
    target_timestamp: datetime
    forecast_window_minutes: int
    predicted_speed_mph: float
    predicted_congestion_index: float = Field(ge=0, le=1)
    risk_level: str  # "green" | "yellow" | "red"
    reasoning_tags: List[str]
    confidence_score: float = Field(ge=0, le=1)
    model_type: str
    last_updated: Optional[datetime] = None


# API Response Schemas
class SegmentsResponse(BaseModel):
    """Response for segments query"""
    segments: List[SegmentState]
    count: int
    timestamp: datetime
    data_freshness_minutes: Optional[int] = None  # Minutes since last data update


class ZonesResponse(BaseModel):
    """Response for zones query"""
    zones: List[ZoneState]
    count: int
    timestamp: datetime


class PredictionsResponse(BaseModel):
    """Response for predictions query"""
    predictions: List[PredictedSegment]
    count: int
    timestamp: datetime


class ValidationMetrics(BaseModel):
    """Validation metrics response"""
    timestamp: datetime
    mae_speed: Optional[float] = None
    sensor_reliability_score: Optional[float] = None
    prediction_accuracy: Optional[float] = None
    status: str  # "pass" | "warning" | "fail"
    details: dict

