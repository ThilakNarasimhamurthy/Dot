"""
MTA GTFS-Realtime API Client
Supports both real API calls and mock data based on USE_MOCKS config
"""
import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import GTFS-RT bindings, fallback gracefully if not available
try:
    from google.transit import gtfs_realtime_pb2
    GTFS_RT_AVAILABLE = True
except ImportError:
    GTFS_RT_AVAILABLE = False
    logger.warning("gtfs-realtime-bindings not installed. Install with: pip install gtfs-realtime-bindings")


class TransitMTAClient:
    """Client for MTA GTFS-Realtime feeds"""
    
    def __init__(self):
        self.api_key = settings.mta_api_key
        self.vehicle_url = f"{settings.mta_gtfs_vehicle_url}?key={self.api_key}" if self.api_key else settings.mta_gtfs_vehicle_url
        self.tripupdates_url = f"{settings.mta_gtfs_tripupdates_url}?key={self.api_key}" if self.api_key else settings.mta_gtfs_tripupdates_url
        self.alerts_url = f"{settings.mta_gtfs_alerts_url}?key={self.api_key}" if self.api_key else settings.mta_gtfs_alerts_url
        self.use_mock = settings.use_mocks or not self.api_key or self.api_key == "your_mta_key_here"
    
    async def fetch_transit_data(self) -> List[Dict]:
        """
        Fetch transit delay data from MTA GTFS-RT
        
        Returns:
            List of normalized transit trip records with delay information
        """
        if self.use_mock:
            logger.info("Using MOCK data for MTA GTFS-RT")
            return self._mock_transit_data()
        
        if not GTFS_RT_AVAILABLE:
            logger.error("GTFS-RT bindings not available, falling back to mock")
            return self._mock_transit_data()
        
        try:
            vehicle_data = await self.get_mta_vehicle_positions()
            trip_updates = await self.get_mta_trip_updates()
            # Combine both sources
            all_trips = vehicle_data + trip_updates
            return all_trips
        except Exception as e:
            logger.error(f"Error fetching MTA data: {e}", exc_info=True)
            if settings.environment == "production":
                return []
            logger.warning("Falling back to mock data due to error")
            return self._mock_transit_data()
    
    async def get_mta_vehicle_positions(self) -> List[Dict]:
        """
        Fetch vehicle positions from MTA GTFS-RT feed
        
        Returns:
            List of vehicle position records
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"x-api-key": self.api_key} if self.api_key else {}
                response = await client.get(self.vehicle_url, headers=headers)
                response.raise_for_status()
                
                # Parse protobuf
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(response.content)
                
                trips = []
                for entity in feed.entity:
                    if entity.HasField('vehicle'):
                        vehicle = entity.vehicle
                        position = vehicle.position
                        
                        # Calculate delay if trip update is available
                        delay_seconds = 0
                        if vehicle.HasField('current_status'):
                            # Estimate delay from position and schedule
                            delay_seconds = 0  # Would need schedule data to calculate
                        
                        trips.append({
                            "trip_id": vehicle.trip.trip_id if vehicle.HasField('trip') else None,
                            "route_id": vehicle.trip.route_id if vehicle.HasField('trip') else None,
                            "vehicle_id": vehicle.vehicle.id if vehicle.HasField('vehicle') else entity.id,
                            "stop_id": vehicle.current_stop_sequence if vehicle.HasField('current_stop_sequence') else None,
                            "delay_seconds": delay_seconds,
                            "arrival_time": None,  # Would need trip updates
                            "departure_time": None,
                            "latitude": position.latitude if position else 0.0,
                            "longitude": position.longitude if position else 0.0,
                            "timestamp": datetime.utcnow()
                        })
                
                return trips
        except Exception as e:
            logger.error(f"Error fetching vehicle positions: {e}")
            return []
    
    async def get_mta_trip_updates(self) -> List[Dict]:
        """
        Fetch trip updates (delays) from MTA GTFS-RT feed
        
        Returns:
            List of trip update records with delay information
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"x-api-key": self.api_key} if self.api_key else {}
                response = await client.get(self.tripupdates_url, headers=headers)
                response.raise_for_status()
                
                # Parse protobuf
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(response.content)
                
                trips = []
                for entity in feed.entity:
                    if entity.HasField('trip_update'):
                        trip_update = entity.trip_update
                        trip = trip_update.trip
                        
                        # Get delay from stop time updates
                        delay_seconds = 0
                        arrival_time = None
                        departure_time = None
                        
                        if trip_update.stop_time_update:
                            # Use first stop time update for delay
                            stop_update = trip_update.stop_time_update[0]
                            if stop_update.HasField('arrival'):
                                if stop_update.arrival.HasField('delay'):
                                    delay_seconds = stop_update.arrival.delay
                                if stop_update.arrival.HasField('time'):
                                    arrival_time = datetime.fromtimestamp(stop_update.arrival.time)
                            
                            if stop_update.HasField('departure'):
                                if stop_update.departure.HasField('delay'):
                                    delay_seconds = max(delay_seconds, stop_update.departure.delay)
                                if stop_update.departure.HasField('time'):
                                    departure_time = datetime.fromtimestamp(stop_update.departure.time)
                        
                        # Get vehicle position if available
                        vehicle = trip_update.vehicle
                        latitude = 0.0
                        longitude = 0.0
                        if vehicle and vehicle.HasField('vehicle'):
                            # Position would be in vehicle positions feed
                            pass
                        
                        trips.append({
                            "trip_id": trip.trip_id if trip.HasField('trip_id') else None,
                            "route_id": trip.route_id if trip.HasField('route_id') else None,
                            "vehicle_id": vehicle.vehicle.id if vehicle and vehicle.HasField('vehicle') else None,
                            "stop_id": stop_update.stop_id if trip_update.stop_time_update else None,
                            "delay_seconds": delay_seconds,
                            "arrival_time": arrival_time,
                            "departure_time": departure_time,
                            "latitude": latitude,
                            "longitude": longitude,
                            "timestamp": datetime.utcnow()
                        })
                
                return trips
        except Exception as e:
            logger.error(f"Error fetching trip updates: {e}")
            return []
    
    def _mock_transit_data(self) -> List[Dict]:
        """Generate realistic mock transit delay data"""
        import random
        
        now = datetime.utcnow()
        routes = ["M1", "M2", "M3", "M4", "B1", "B2", "Q1", "Q2", "1", "2", "3", "4", "5", "6"]
        
        mock_trips = []
        for i in range(15):  # Generate 15 mock transit trips
            route = random.choice(routes)
            delay_seconds = random.randint(0, 600) if random.random() > 0.3 else 0  # 30% on-time
            
            mock_trips.append({
                "trip_id": f"trip_{random.randint(10000, 99999)}",
                "route_id": route,
                "vehicle_id": f"vehicle_{random.randint(1000, 9999)}",
                "stop_id": f"stop_{random.randint(100, 999)}",
                "delay_seconds": delay_seconds,
                "arrival_time": now + timedelta(minutes=random.randint(1, 30)),
                "departure_time": now + timedelta(minutes=random.randint(2, 35)),
                "latitude": 40.7128 + random.uniform(-0.15, 0.15),
                "longitude": -74.0060 + random.uniform(-0.15, 0.15),
                "timestamp": now
            })
        
        return mock_trips

