"""
NYC DOT OpenData Traffic Speeds Client
Supports both real API calls and mock data based on USE_MOCKS config
"""
import httpx
import logging
from typing import List, Dict
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class TrafficDOTClient:
    """Client for NYC DOT OpenData Traffic Speeds"""
    
    def __init__(self):
        self.speeds_url = settings.nyc_dot_traffic_speeds_url
        self.volume_url = settings.nyc_dot_traffic_volume_url
        self.collisions_url = settings.nyc_dot_collisions_url
        self.use_mock = settings.use_mocks
    
    async def fetch_traffic_speeds(self) -> List[Dict]:
        """
        Fetch traffic speed data from NYC DOT OpenData
        
        Returns:
            List of normalized traffic speed records
        """
        if self.use_mock:
            logger.info("Using MOCK data for NYC DOT OpenData")
            return self._mock_traffic_speeds()
        
        try:
            raw_data = await self._fetch_dot_raw()
            return self._parse_response(raw_data)
        except Exception as e:
            logger.error(f"Error fetching NYC DOT data: {e}", exc_info=True)
            if settings.environment == "production":
                return []
            logger.warning("Falling back to mock data due to error")
            return self._mock_traffic_speeds()
    
    async def _fetch_dot_raw(self) -> List[Dict]:
        """
        Low-level HTTP call to NYC DOT OpenData (Socrata API)
        Fetches from multiple datasets: speeds, volume, collisions
        
        Returns:
            Combined raw API response as list of dictionaries
        """
        all_data = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch traffic speeds
            try:
                response = await client.get(
                    self.speeds_url,
                    params={
                        "$limit": 500,
                        "$order": "data_as_of DESC"
                    },
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()
                speeds_data = response.json()
                # Tag the source
                for item in speeds_data:
                    item["_source"] = "traffic_speeds"
                all_data.extend(speeds_data)
            except Exception as e:
                logger.warning(f"Error fetching traffic speeds: {e}")
            
            # Fetch traffic volume (optional - can be heavy)
            try:
                response = await client.get(
                    self.volume_url,
                    params={
                        "$limit": 200,
                        "$order": "date DESC"
                    },
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()
                volume_data = response.json()
                for item in volume_data:
                    item["_source"] = "traffic_volume"
                all_data.extend(volume_data)
            except Exception as e:
                logger.warning(f"Error fetching traffic volume: {e}")
        
        return all_data
    
    def _parse_response(self, data: List[Dict]) -> List[Dict]:
        """
        Parse NYC DOT OpenData (Socrata) response into normalized format
        
        Args:
            data: Raw API response list
        
        Returns:
            List of normalized segment records
        """
        segments = []
        
        for item in data:
            try:
                source_type = item.get("_source", "traffic_speeds")
                
                # Extract segment ID (varies by dataset)
                segment_id = (
                    item.get("segment_id") or 
                    item.get("segmentid") or 
                    item.get("id") or
                    item.get("link_id") or
                    item.get("location") or
                    f"dot_seg_{len(segments) + 1}"
                )
                
                # Extract speed (field names vary by dataset)
                speed_raw = None
                if source_type == "traffic_speeds":
                    speed_raw = (
                        item.get("speed") or 
                        item.get("speed_mph") or 
                        item.get("current_speed") or
                        item.get("avg_speed") or
                        item.get("speed_mph_nbe")
                    )
                elif source_type == "traffic_volume":
                    # Volume data might not have speed, skip for now
                    continue
                
                if speed_raw:
                    speed_mph = float(speed_raw)
                else:
                    continue  # Skip if no speed
                
                # Extract location (Socrata may have lat/lon or geometry)
                latitude = None
                longitude = None
                
                # Try direct lat/lon fields
                lat = item.get("latitude") or item.get("lat") or item.get("y")
                lon = item.get("longitude") or item.get("lon") or item.get("x") or item.get("lng")
                
                if lat and lon:
                    latitude = float(lat)
                    longitude = float(lon)
                elif "location" in item and item["location"]:
                    # Socrata location object
                    loc = item["location"]
                    if isinstance(loc, dict):
                        latitude = float(loc.get("latitude", loc.get("coordinates", [None, None])[1] or 0))
                        longitude = float(loc.get("longitude", loc.get("coordinates", [None, None])[0] or 0))
                
                if not latitude or not longitude:
                    continue  # Skip if no location
                
                # Extract timestamp
                timestamp_str = (
                    item.get("timestamp") or 
                    item.get("date") or 
                    item.get("created_at") or
                    item.get("measurement_timestamp")
                )
                if timestamp_str:
                    try:
                        # Parse various timestamp formats
                        if isinstance(timestamp_str, str):
                            # Try common formats
                            from dateutil import parser
                            timestamp = parser.parse(timestamp_str)
                        else:
                            timestamp = datetime.utcnow()
                    except:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
                
                normalized = {
                    "segment_id": str(segment_id),
                    "speed_mph": speed_mph,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": timestamp
                }
                
                segments.append(normalized)
                
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Error parsing NYC DOT segment: {e}, skipping item")
                continue
        
        logger.info(f"Parsed {len(segments)} segments from NYC DOT OpenData")
        return segments
    
    def _mock_traffic_speeds(self) -> List[Dict]:
        """Generate realistic mock traffic speed data"""
        import random
        
        mock_data = [
            {
                "segment_id": "dot_seg_001",
                "speed_mph": random.uniform(18.0, 32.0),
                "latitude": 40.7589 + random.uniform(-0.05, 0.05),
                "longitude": -73.9851 + random.uniform(-0.05, 0.05),
                "timestamp": datetime.utcnow()
            },
            {
                "segment_id": "dot_seg_002",
                "speed_mph": random.uniform(14.0, 28.0),
                "latitude": 40.6892 + random.uniform(-0.05, 0.05),
                "longitude": -73.9442 + random.uniform(-0.05, 0.05),
                "timestamp": datetime.utcnow()
            },
            {
                "segment_id": "dot_seg_003",
                "speed_mph": random.uniform(16.0, 30.0),
                "latitude": 40.7282 + random.uniform(-0.05, 0.05),
                "longitude": -73.7949 + random.uniform(-0.05, 0.05),
                "timestamp": datetime.utcnow()
            }
        ]
        
        return mock_data

