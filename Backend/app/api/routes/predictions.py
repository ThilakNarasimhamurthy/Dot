"""
API routes for predictions
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
from app.database import get_database
from app.models.schemas import PredictionsResponse, PredictedSegment

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("", response_model=PredictionsResponse)
async def get_predictions(
    segment_id: Optional[str] = None,
    window_minutes: Optional[int] = Query(None, ge=15, le=30),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get congestion predictions
    
    Args:
        segment_id: Optional segment filter
        window_minutes: Optional forecast window filter (15 or 30)
        limit: Maximum number of predictions to return
    
    Returns:
        Predictions
    """
    db = get_database()
    
    if db is None:
        return PredictionsResponse(
            predictions=[],
            count=0,
            timestamp=datetime.utcnow()
        )
    
    # Build query
    query = {}
    if segment_id:
        query["segment_id"] = segment_id
    if window_minutes:
        query["forecast_window_minutes"] = window_minutes
    
    # Get most recent predictions (prioritize recently updated ones)
    cursor = db.predicted_segments.find(query).sort([
        ("last_updated", -1),  # Most recently updated first
        ("target_timestamp", 1)  # Then by target time
    ]).limit(limit)
    predictions_docs = await cursor.to_list(length=limit)
    
    # Convert to Pydantic models (handle missing fields gracefully)
    predictions = []
    for doc in predictions_docs:
        try:
            # Clean NaN values before parsing
            import math
            cleaned_doc = {}
            for key, value in doc.items():
                if isinstance(value, float) and math.isnan(value):
                    cleaned_doc[key] = None
                else:
                    cleaned_doc[key] = value
            
            prediction = PredictedSegment(**cleaned_doc)
            predictions.append(prediction)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to parse prediction document {doc.get('segment_id', 'unknown')}: {e}")
            # Skip invalid documents
            continue
    
    return PredictionsResponse(
        predictions=predictions,
        count=len(predictions),
        timestamp=datetime.utcnow()
    )


@router.get("/{segment_id}", response_model=PredictionsResponse)
async def get_segment_predictions(segment_id: str):
    """
    Get predictions for a specific segment
    
    Args:
        segment_id: Segment identifier
    
    Returns:
        Predictions for the segment
    """
    db = get_database()
    
    if db is None:
        return PredictionsResponse(
            predictions=[],
            count=0,
            timestamp=datetime.utcnow()
        )
    
    predictions_docs = await db.predicted_segments.find({
        "segment_id": segment_id
    }).sort([
        ("last_updated", -1),
        ("target_timestamp", 1)
    ]).to_list(length=10)
    
    predictions = [PredictedSegment(**doc) for doc in predictions_docs]
    
    return PredictionsResponse(
        predictions=predictions,
        count=len(predictions),
        timestamp=datetime.utcnow()
    )

