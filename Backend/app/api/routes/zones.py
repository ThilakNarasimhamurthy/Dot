"""
API routes for zone data
"""
import math
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
from datetime import datetime
from app.database import get_database
from app.models.schemas import ZonesResponse, ZoneState

router = APIRouter(prefix="/api/zones", tags=["zones"])


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


@router.get("/current", response_model=ZonesResponse)
async def get_current_zones(borough: Optional[str] = None):
    """
    Get current zone states
    
    Returns:
        Current zone states
    """
    db = get_database()
    
    if db is None:
        return ZonesResponse(
            zones=[],
            count=0,
            timestamp=datetime.utcnow()
        )
    
    # Get most recent timestamp bucket
    latest = await db.zones_state.find_one(
        {},
        sort=[("timestamp_bucket", -1)]
    )
    
    if not latest:
        return ZonesResponse(
            zones=[],
            count=0,
            timestamp=datetime.utcnow()
        )
    
    latest_bucket = latest["timestamp_bucket"]
    
    # Build query
    query = {"timestamp_bucket": latest_bucket}
    if borough:
        query["borough"] = borough
    
    # Fetch zones
    cursor = db.zones_state.find(query)
    zones_docs = await cursor.to_list(length=100)
    
    # Convert to Pydantic models (handle missing fields gracefully)
    zones = []
    for doc in zones_docs:
        try:
            # Clean NaN values before parsing
            cleaned_doc = clean_nan_values(doc)
            # Ensure borough field exists (backward compatibility)
            if "borough" not in cleaned_doc or cleaned_doc["borough"] is None:
                # Try to infer from zone_id or bounding_box
                zone_id_lower = cleaned_doc.get("zone_id", "").lower()
                if "manhattan" in zone_id_lower or "cbd" in zone_id_lower:
                    cleaned_doc["borough"] = "Manhattan"
                elif "brooklyn" in zone_id_lower or "bk" in zone_id_lower:
                    cleaned_doc["borough"] = "Brooklyn"
                elif "queens" in zone_id_lower or "qn" in zone_id_lower:
                    cleaned_doc["borough"] = "Queens"
                elif "bronx" in zone_id_lower or "bx" in zone_id_lower:
                    cleaned_doc["borough"] = "Bronx"
                elif "staten" in zone_id_lower or "si" in zone_id_lower:
                    cleaned_doc["borough"] = "Staten Island"
                elif "bounding_box" in cleaned_doc and cleaned_doc["bounding_box"]:
                    # Use center of bounding box
                    bbox = cleaned_doc["bounding_box"]
                    center_lat = (bbox.get("min_lat", 0) + bbox.get("max_lat", 0)) / 2
                    center_lon = (bbox.get("min_lon", 0) + bbox.get("max_lon", 0)) / 2
                    if center_lat and center_lon:
                        if 40.7 <= center_lat <= 40.8 and -74.05 <= center_lon <= -73.95:
                            cleaned_doc["borough"] = "Manhattan"
                        elif 40.6 <= center_lat <= 40.75 and -74.05 <= center_lon <= -73.9:
                            cleaned_doc["borough"] = "Brooklyn"
                        elif 40.7 <= center_lat <= 40.8 and -73.95 <= center_lon <= -73.7:
                            cleaned_doc["borough"] = "Queens"
                        elif 40.8 <= center_lat <= 40.9 and -73.95 <= center_lon <= -73.85:
                            cleaned_doc["borough"] = "Bronx"
                        elif 40.5 <= center_lat <= 40.65 and -74.3 <= center_lon <= -74.1:
                            cleaned_doc["borough"] = "Staten Island"
                        else:
                            cleaned_doc["borough"] = "Manhattan"  # default
                    else:
                        cleaned_doc["borough"] = None
                else:
                    cleaned_doc["borough"] = None
            
            # Ensure all required fields exist, use defaults for missing optional fields
            zone = ZoneState(**cleaned_doc)
            zones.append(zone)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to parse zone document {doc.get('zone_id', 'unknown')}: {e}")
            # Skip invalid documents
            continue
    
    return ZonesResponse(
        zones=zones,
        count=len(zones),
        timestamp=datetime.utcnow()
    )


@router.get("/{zone_id}", response_model=ZoneState)
async def get_zone(zone_id: str):
    """
    Get current state for a specific zone
    
    Args:
        zone_id: Zone identifier
    
    Returns:
        Zone state
    """
    db = get_database()
    
    if db is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not available")
    
    zone = await db.zones_state.find_one(
        {"zone_id": zone_id},
        sort=[("timestamp_bucket", -1)]
    )
    
    if not zone:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Clean NaN values before parsing
    cleaned_zone = clean_nan_values(zone)
    return ZoneState(**cleaned_zone)

