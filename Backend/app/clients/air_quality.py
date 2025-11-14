"""
Air Quality API Client (NYC DOHMH or AirNow fallback)
TODO: Replace mock functions with real API calls
"""
import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class AirQualityClient:
    """Client for air quality data"""
    
    def __init__(self):
        self.airnow_api_key = settings.airnow_api_key
        self.nyc_url = settings.nyc_air_quality_url
        self.airnow_base_url = settings.airnow_base_url
        self.use_mock = settings.use_mocks
    
    async def fetch_air_quality_data(self) -> List[Dict]:
        """
        Fetch air quality data from DOHMH or AirNow
        
        Returns:
            List of air quality sensor readings
        """
        if self.use_mock:
            logger.warning("Using MOCK data for Air Quality")
            return self._mock_air_quality_data()
        
        # Try NYC DOHMH/OpenData first
        try:
            raw_data = await self._fetch_nyc_air_quality_raw()
            return self._parse_nyc_response(raw_data)
        except Exception as e:
            logger.warning(f"NYC air quality endpoint failed: {e}, trying AirNow")
            return await self._fetch_airnow_data()
    
    async def _fetch_nyc_air_quality_raw(self) -> List[Dict]:
        """Low-level HTTP call to NYC DOHMH/OpenData"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.nyc_url,
                params={"$limit": 100, "$order": "date DESC"},
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
    
    async def _fetch_airnow_data(self) -> List[Dict]:
        """Fetch from AirNow API as fallback"""
        if not self.airnow_api_key or self.airnow_api_key == "optional_airnow_key_if_used":
            logger.warning("AirNow API key not configured, returning empty list")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # NYC zip codes
                zip_codes = ["10001", "10002", "11201", "11101", "11368"]
                all_readings = []
                
                for zip_code in zip_codes:
                    response = await client.get(
                        self.airnow_base_url,
                        params={
                            "format": "application/json",
                            "zipCode": zip_code,
                            "API_KEY": self.airnow_api_key,
                            "distance": 25
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    all_readings.extend(self._parse_airnow_response(data, zip_code))
                
                return all_readings
        except Exception as e:
            logger.error(f"Error fetching AirNow data: {e}")
            if settings.environment == "production":
                return []
            return self._mock_air_quality_data()
    
    def _parse_nyc_response(self, data: List[Dict]) -> List[Dict]:
        """Parse NYC DOHMH/OpenData API response"""
        readings = []
        for item in data:
            try:
                sensor_id = (
                    item.get("sensor_id") or 
                    item.get("id") or 
                    item.get("station_id") or
                    f"nyc_aq_{len(readings) + 1}"
                )
                
                pm25_raw = item.get("pm25") or item.get("pm2_5") or item.get("pm_2_5")
                if pm25_raw:
                    pm25 = float(pm25_raw)
                else:
                    continue  # Skip if no PM2.5
                
                # Extract location
                lat = item.get("latitude") or item.get("lat") or item.get("y")
                lon = item.get("longitude") or item.get("lon") or item.get("x") or item.get("lng")
                
                if not lat or not lon:
                    # Try location object
                    if "location" in item and item["location"]:
                        loc = item["location"]
                        if isinstance(loc, dict):
                            lat = loc.get("latitude", loc.get("coordinates", [None, None])[1])
                            lon = loc.get("longitude", loc.get("coordinates", [None, None])[0])
                
                if not lat or not lon:
                    continue  # Skip if no location
                
                readings.append({
                    "sensor_id": str(sensor_id),
                    "pm25": pm25,
                    "pm10": item.get("pm10"),
                    "aqi": item.get("aqi") or item.get("air_quality_index"),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "timestamp": datetime.utcnow(),
                    "source": "dohmn"
                })
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Error parsing NYC air quality reading: {e}")
                continue
        
        logger.info(f"Parsed {len(readings)} air quality readings from NYC")
        return readings
    
    def _parse_airnow_response(self, data: List[Dict], zip_code: str) -> List[Dict]:
        """Parse AirNow API response"""
        readings = []
        for item in data:
            if item.get('ParameterName') == 'PM2.5':
                readings.append({
                    "sensor_id": f"airnow_{zip_code}",
                    "pm25": float(item.get('Value', 0)),
                    "pm10": None,  # AirNow may not provide PM10
                    "aqi": int(item.get('AQI', 0)),
                    "latitude": float(item.get('Latitude', 0)),
                    "longitude": float(item.get('Longitude', 0)),
                    "timestamp": datetime.utcnow(),
                    "source": "airnow"
                })
        return readings
    
    def _mock_air_quality_data(self) -> List[Dict]:
        """Generate realistic mock air quality data"""
        import random
        
        # NYC sensor locations
        sensors = [
            {"sensor_id": "aq_sensor_001", "lat": 40.7128, "lon": -74.0060, "name": "Lower Manhattan"},
            {"sensor_id": "aq_sensor_002", "lat": 40.7589, "lon": -73.9851, "name": "Midtown"},
            {"sensor_id": "aq_sensor_003", "lat": 40.6892, "lon": -73.9442, "name": "Brooklyn"},
            {"sensor_id": "aq_sensor_004", "lat": 40.7282, "lon": -73.7949, "name": "Queens"},
            {"sensor_id": "aq_sensor_005", "lat": 40.7831, "lon": -73.9712, "name": "Upper Manhattan"},
        ]
        
        mock_readings = []
        for sensor in sensors:
            # PM2.5 typically ranges 5-50 in NYC, higher during congestion
            pm25 = random.uniform(8.0, 35.0)
            
            mock_readings.append({
                "sensor_id": sensor["sensor_id"],
                "pm25": round(pm25, 2),
                "pm10": round(pm25 * 1.2, 2) if random.random() > 0.3 else None,
                "aqi": int(pm25 * 2.5) if pm25 > 12 else random.randint(20, 50),
                "latitude": sensor["lat"] + random.uniform(-0.01, 0.01),
                "longitude": sensor["lon"] + random.uniform(-0.01, 0.01),
                "timestamp": datetime.utcnow()
            })
        
        return mock_readings

