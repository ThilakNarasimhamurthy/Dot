"""
API routes for segment data
"""
import math
from fastapi import APIRouter, Query
from typing import Optional, Dict, Any
from datetime import datetime
from app.database import get_database
from app.models.schemas import SegmentsResponse, SegmentState

router = APIRouter(prefix="/api/segments", tags=["segments"])


def clean_nan_values(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Replace NaN values with None in document"""
    cleaned = {}
    for key, value in doc.items():
        if isinstance(value, float) and math.isnan(value):
            cleaned[key] = None
        elif isinstance(value, dict):
            cleaned[key] = clean_nan_values(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_nan_values(item) if isinstance(item, dict) else (None if isinstance(item, float) and math.isnan(item) else item)
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


@router.get("/current", response_model=SegmentsResponse)
async def get_current_segments(
    limit: int = Query(100, ge=1, le=1000),
    zone_id: Optional[str] = None,
    borough: Optional[str] = None
):
    """
    Get current segment states
    
    Args:
        limit: Maximum number of segments to return
        zone_id: Optional zone filter
    
    Returns:
        Current segment states
    """
    db = get_database()
    
    if db is None:
        return SegmentsResponse(
            segments=[],
            count=0,
            timestamp=datetime.utcnow(),
            data_freshness_minutes=None
        )
    
    # Get most recent timestamp bucket
    latest = await db.segments_state.find_one(
        {},
        sort=[("timestamp_bucket", -1)]
    )
    
    if not latest:
        return SegmentsResponse(
            segments=[],
            count=0,
            timestamp=datetime.utcnow(),
            data_freshness_minutes=None
        )
    
    latest_bucket = latest["timestamp_bucket"]
    
    # Calculate data freshness
    if isinstance(latest_bucket, datetime):
        age = datetime.utcnow() - latest_bucket
        freshness_minutes = int(age.total_seconds() / 60)
    else:
        freshness_minutes = None
    
    # Build query
    query = {"timestamp_bucket": latest_bucket}
    if zone_id:
        query["zone_id"] = zone_id
    if borough:
        query["borough"] = borough
    
    # Fetch segments
    cursor = db.segments_state.find(query).limit(limit)
    segments_docs = await cursor.to_list(length=limit)
    
    # Convert to Pydantic models (handle missing fields gracefully)
    segments = []
    for doc in segments_docs:
        try:
            # Clean NaN values before parsing
            cleaned_doc = clean_nan_values(doc)
            # Ensure borough field exists (backward compatibility)
            if "borough" not in cleaned_doc or cleaned_doc["borough"] is None:
                # Try to infer from coordinates if available
                if "latitude" in cleaned_doc and "longitude" in cleaned_doc:
                    lat = cleaned_doc.get("latitude")
                    lon = cleaned_doc.get("longitude")
                    if lat and lon:
                        # Simple borough detection (can be improved)
                        if 40.7 <= lat <= 40.8 and -74.05 <= lon <= -73.95:
                            cleaned_doc["borough"] = "Manhattan"
                        elif 40.6 <= lat <= 40.75 and -74.05 <= lon <= -73.9:
                            cleaned_doc["borough"] = "Brooklyn"
                        elif 40.7 <= lat <= 40.8 and -73.95 <= lon <= -73.7:
                            cleaned_doc["borough"] = "Queens"
                        elif 40.8 <= lat <= 40.9 and -73.95 <= lon <= -73.85:
                            cleaned_doc["borough"] = "Bronx"
                        elif 40.5 <= lat <= 40.65 and -74.3 <= lon <= -74.1:
                            cleaned_doc["borough"] = "Staten Island"
                        else:
                            cleaned_doc["borough"] = "Manhattan"  # default
                    else:
                        cleaned_doc["borough"] = None
                else:
                    cleaned_doc["borough"] = None
            
            segment = SegmentState(**cleaned_doc)
            segments.append(segment)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to parse segment document {doc.get('segment_id', 'unknown')}: {e}")
            # Skip invalid documents
            continue
    
    return SegmentsResponse(
        segments=segments,
        count=len(segments),
        timestamp=datetime.utcnow(),
        data_freshness_minutes=freshness_minutes
    )


@router.get("/{segment_id}", response_model=SegmentState)
async def get_segment(segment_id: str):
    """
    Get current state for a specific segment
    
    Args:
        segment_id: Segment identifier
    
    Returns:
        Segment state
    """
    db = get_database()
    
    if db is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not available")
    
    segment = await db.segments_state.find_one(
        {"segment_id": segment_id},
        sort=[("timestamp_bucket", -1)]
    )
    
    if not segment:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # Clean NaN values before parsing
    cleaned_segment = clean_nan_values(segment)
    return SegmentState(**cleaned_segment)

