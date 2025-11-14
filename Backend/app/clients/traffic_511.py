"""
511NY Traffic API Client
Supports both real API calls and mock data based on USE_MOCKS config
"""
import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class Traffic511Client:
    """Client for 511NY Traffic API"""
    
    def __init__(self):
        self.api_key = settings.ny511_api_key
        self.base_url = settings.ny511_base_url
        # Use mocks if flag is set OR if API key is missing
        self.use_mock = settings.use_mocks or not self.api_key or self.api_key == "your_511ny_key_here"
    
    async def fetch_traffic_data(self) -> List[Dict]:
        """
        Fetch traffic data from 511NY API
        
        Returns:
            List of normalized traffic segment data
        """
        if self.use_mock:
            logger.info("Using MOCK data for 511NY API")
            return self._mock_traffic_data()
        
        try:
            raw_data = await self._fetch_511ny_raw()
            return self._parse_response(raw_data)
        except Exception as e:
            logger.error(f"Error fetching 511NY data: {e}", exc_info=True)
            # Don't fallback to mock in production - return empty list
            if settings.environment == "production":
                return []
            # Only fallback to mock in development
            logger.warning("Falling back to mock data due to error")
            return self._mock_traffic_data()
    
    async def _fetch_511ny_raw(self) -> Dict:
        """
        Low-level HTTP call to 511NY API
        
        Returns:
            Raw API response as dictionary
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 511NY API typically uses query parameter for API key
            # Adjust endpoint and auth method based on actual API documentation
            response = await client.get(
                f"{self.base_url}/segments",
                params={
                    "key": self.api_key,
                    "format": "json"
                },
                headers={
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()
    
    def _parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse 511NY API response into normalized format
        
        Args:
            data: Raw API response dictionary
        
        Returns:
            List of normalized segment records
        """
        segments = []
        
        # Handle different possible response structures
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common response keys
            items = data.get("segments", data.get("data", data.get("results", [])))
            if not items and "features" in data:
                # GeoJSON format
                items = data["features"]
        
        for item in items:
            try:
                # Extract segment ID
                segment_id = (
                    item.get("segment_id") or 
                    item.get("id") or 
                    item.get("segmentId") or
                    item.get("properties", {}).get("segment_id") or
                    f"511_seg_{len(segments) + 1}"
                )
                
                # Extract speed (convert to mph if needed)
                speed_raw = item.get("speed") or item.get("speed_mph") or item.get("currentSpeed")
                if speed_raw:
                    speed_mph = float(speed_raw)
                    # Convert from km/h to mph if needed (assuming > 100 is km/h)
                    if speed_mph > 100:
                        speed_mph = speed_mph / 1.60934
                else:
                    continue  # Skip if no speed data
                
                # Extract location
                geometry = item.get("geometry", {})
                if geometry and "coordinates" in geometry:
                    coords = geometry["coordinates"]
                    longitude = float(coords[0])
                    latitude = float(coords[1])
                else:
                    lat = item.get("latitude") or item.get("lat")
                    lon = item.get("longitude") or item.get("lon") or item.get("lng")
                    if lat and lon:
                        latitude = float(lat)
                        longitude = float(lon)
                    else:
                        continue  # Skip if no location
                
                # Extract incident/roadwork info
                incident_type = item.get("incident_type") or item.get("incidentType")
                incident_description = item.get("incident_description") or item.get("description")
                roadwork_flag = item.get("roadwork", False) or item.get("road_work", False)
                
                # Extract segment name
                segment_name = (
                    item.get("segment_name") or 
                    item.get("name") or 
                    item.get("road_name") or
                    item.get("properties", {}).get("name", "")
                )
                
                normalized = {
                    "segment_id": str(segment_id),
                    "segment_name": str(segment_name),
                    "speed_mph": speed_mph,
                    "incident_type": incident_type,
                    "incident_description": incident_description,
                    "roadwork_flag": bool(roadwork_flag),
                    "camera_id": item.get("camera_id") or item.get("cameraId"),
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": datetime.utcnow()
                }
                
                segments.append(normalized)
                
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Error parsing 511NY segment: {e}, skipping item")
                continue
        
        logger.info(f"Parsed {len(segments)} segments from 511NY API")
        return segments
    
    def _mock_traffic_data(self) -> List[Dict]:
        """Generate realistic mock traffic data for testing"""
        import random
        from datetime import datetime, timedelta
        
        # Mock segments in NYC (Manhattan, Brooklyn, Queens)
        mock_segments = [
            {
                "segment_id": "511_seg_001",
                "segment_name": "FDR Drive - Lower Manhattan",
                "speed_mph": random.uniform(15.0, 35.0),
                "incident_type": None if random.random() > 0.1 else random.choice(["accident", "breakdown", "roadwork"]),
                "incident_description": None,
                "roadwork_flag": random.random() > 0.9,
                "camera_id": f"cam_{random.randint(1000, 9999)}" if random.random() > 0.5 else None,
                "latitude": 40.7128 + random.uniform(-0.1, 0.1),
                "longitude": -74.0060 + random.uniform(-0.1, 0.1),
                "timestamp": datetime.utcnow()
            },
            {
                "segment_id": "511_seg_002",
                "segment_name": "Brooklyn Bridge Approach",
                "speed_mph": random.uniform(8.0, 25.0),
                "incident_type": None if random.random() > 0.15 else "accident",
                "incident_description": "Lane closure" if random.random() > 0.7 else None,
                "roadwork_flag": False,
                "camera_id": f"cam_{random.randint(1000, 9999)}",
                "latitude": 40.6892 + random.uniform(-0.05, 0.05),
                "longitude": -73.9442 + random.uniform(-0.05, 0.05),
                "timestamp": datetime.utcnow()
            },
            {
                "segment_id": "511_seg_003",
                "segment_name": "Queens Boulevard - Midtown",
                "speed_mph": random.uniform(12.0, 30.0),
                "incident_type": None,
                "incident_description": None,
                "roadwork_flag": random.random() > 0.85,
                "camera_id": None,
                "latitude": 40.7282 + random.uniform(-0.08, 0.08),
                "longitude": -73.7949 + random.uniform(-0.08, 0.08),
                "timestamp": datetime.utcnow()
            },
            {
                "segment_id": "511_seg_004",
                "segment_name": "West Side Highway - Upper Manhattan",
                "speed_mph": random.uniform(20.0, 40.0),
                "incident_type": None,
                "incident_description": None,
                "roadwork_flag": False,
                "camera_id": f"cam_{random.randint(1000, 9999)}",
                "latitude": 40.7831 + random.uniform(-0.05, 0.05),
                "longitude": -73.9712 + random.uniform(-0.05, 0.05),
                "timestamp": datetime.utcnow()
            },
            {
                "segment_id": "511_seg_005",
                "segment_name": "BQE - Brooklyn",
                "speed_mph": random.uniform(10.0, 28.0),
                "incident_type": None if random.random() > 0.12 else "breakdown",
                "incident_description": None,
                "roadwork_flag": random.random() > 0.88,
                "camera_id": None,
                "latitude": 40.6782 + random.uniform(-0.1, 0.1),
                "longitude": -73.9442 + random.uniform(-0.1, 0.1),
                "timestamp": datetime.utcnow()
            }
        ]
        
        return mock_segments

