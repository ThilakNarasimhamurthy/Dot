"""
Agent 2: Cleaning + Correlation Agent
Converts fragmented raw data into usable final fused structure
"""
import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from app.database import get_database
from app.services.imputation import ImputationService
from app.services.correlation import CorrelationService

logger = logging.getLogger(__name__)

# NYC approximate bounds
NYC_MIN_LAT = 40.5
NYC_MAX_LAT = 40.9
NYC_MIN_LON = -74.3
NYC_MAX_LON = -73.7
# Default NYC center (Times Square)
NYC_DEFAULT_LAT = 40.7580
NYC_DEFAULT_LON = -73.9855


class CleaningCorrelationAgent:
    """Agent responsible for cleaning, fusing, and correlating data"""
    
    def __init__(self):
        self.db = get_database()
        self.imputation_service = ImputationService()
        self.correlation_service = CorrelationService()
        # 5-minute bucket size
        self.bucket_minutes = 5
    
    async def process_raw_data(self) -> Dict[str, int]:
        """
        Process raw data: clean, fuse, and create segments_state and zones_state
        
        Returns:
            Dictionary with counts of processed records
        """
        try:
            # Get recent raw data (last hour)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # Process traffic data
            segments_created = await self._process_traffic_data(cutoff_time)
            
            # Process zones (aggregate segments)
            zones_created = await self._process_zones(cutoff_time)
            
            logger.info(f"Processing complete: {segments_created} segments, {zones_created} zones")
            
            return {
                "segments_created": segments_created,
                "zones_created": zones_created
            }
            
        except Exception as e:
            logger.error(f"Error in processing: {e}", exc_info=True)
            return {"segments_created": 0, "zones_created": 0}
    
    def _is_valid_coordinate(self, lat: Optional[float], lon: Optional[float]) -> bool:
        """Check if coordinates are valid for NYC"""
        if lat is None or lon is None:
            return False
        if math.isnan(lat) or math.isnan(lon):
            return False
        if lat == 0.0 and lon == 0.0:
            return False
        # Check if within NYC bounds
        if not (NYC_MIN_LAT <= lat <= NYC_MAX_LAT and NYC_MIN_LON <= lon <= NYC_MAX_LON):
            return False
        return True
    
    async def _impute_coordinates(self, segment_id: str) -> Tuple[float, float]:
        """Try to find valid coordinates from historical data for this segment"""
        try:
            # Look for this segment in historical segments_state
            historical = await self.db.segments_state.find_one(
                {
                    "segment_id": segment_id,
                    "latitude": {"$ne": None, "$exists": True},
                    "longitude": {"$ne": None, "$exists": True}
                },
                sort=[("timestamp_bucket", -1)]
            )
            
            if historical:
                lat = historical.get("latitude")
                lon = historical.get("longitude")
                if self._is_valid_coordinate(lat, lon):
                    logger.info(f"Found historical coordinates for {segment_id}: ({lat}, {lon})")
                    return lat, lon
            
            # Try raw_traffic_511
            raw_511 = await self.db.raw_traffic_511.find_one(
                {
                    "segment_id": segment_id,
                    "latitude": {"$ne": None, "$exists": True},
                    "longitude": {"$ne": None, "$exists": True}
                },
                sort=[("timestamp", -1)]
            )
            
            if raw_511:
                lat = raw_511.get("latitude")
                lon = raw_511.get("longitude")
                if self._is_valid_coordinate(lat, lon):
                    logger.info(f"Found coordinates from raw_511 for {segment_id}: ({lat}, {lon})")
                    return lat, lon
            
            # Try raw_traffic_dot
            raw_dot = await self.db.raw_traffic_dot.find_one(
                {
                    "segment_id": segment_id,
                    "latitude": {"$ne": None, "$exists": True},
                    "longitude": {"$ne": None, "$exists": True}
                },
                sort=[("timestamp", -1)]
            )
            
            if raw_dot:
                lat = raw_dot.get("latitude")
                lon = raw_dot.get("longitude")
                if self._is_valid_coordinate(lat, lon):
                    logger.info(f"Found coordinates from raw_dot for {segment_id}: ({lat}, {lon})")
                    return lat, lon
            
            # Default to NYC center if nothing found
            logger.warning(f"No valid coordinates found for {segment_id}, using default NYC center")
            return NYC_DEFAULT_LAT, NYC_DEFAULT_LON
            
        except Exception as e:
            logger.error(f"Error imputing coordinates for {segment_id}: {e}")
            return NYC_DEFAULT_LAT, NYC_DEFAULT_LON
    
    def _get_borough_from_coordinates(self, lat: float, lon: float) -> str:
        """Determine NYC borough from coordinates"""
        # Manhattan: roughly 40.7-40.8 lat, -74.05 to -73.95 lon
        if 40.7 <= lat <= 40.8 and -74.05 <= lon <= -73.95:
            return "Manhattan"
        # Brooklyn: roughly 40.6-40.75 lat, -74.05 to -73.9 lon
        elif 40.6 <= lat <= 40.75 and -74.05 <= lon <= -73.9:
            return "Brooklyn"
        # Queens: roughly 40.7-40.8 lat, -73.95 to -73.7 lon
        elif 40.7 <= lat <= 40.8 and -73.95 <= lon <= -73.7:
            return "Queens"
        # Bronx: roughly 40.8-40.9 lat, -73.95 to -73.85 lon
        elif 40.8 <= lat <= 40.9 and -73.95 <= lon <= -73.85:
            return "Bronx"
        # Staten Island: roughly 40.5-40.65 lat, -74.3 to -74.1 lon
        elif 40.5 <= lat <= 40.65 and -74.3 <= lon <= -74.1:
            return "Staten Island"
        # Default to Manhattan if unclear
        else:
            return "Manhattan"
    
    async def _validate_and_impute_coordinates(self, segment_id: str, lat: Optional[float], lon: Optional[float]) -> Tuple[float, float]:
        """Validate coordinates and impute if invalid"""
        if self._is_valid_coordinate(lat, lon):
            return lat, lon
        
        # Coordinates are invalid, try to impute
        return await self._impute_coordinates(segment_id)
    
    async def _process_traffic_data(self, cutoff_time: datetime) -> int:
        """Process traffic data and create segments_state"""
        try:
            # Get raw traffic data from both sources
            traffic_511 = await self.db.raw_traffic_511.find({
                "timestamp": {"$gte": cutoff_time}
            }).to_list(length=1000)
            
            traffic_dot = await self.db.raw_traffic_dot.find({
                "timestamp": {"$gte": cutoff_time}
            }).to_list(length=1000)
            
            # Group by segment_id and time bucket
            segments_dict = defaultdict(dict)
            
            # Process 511NY data
            for doc in traffic_511:
                segment_id = doc.get("segment_id")
                if not segment_id:
                    continue
                
                timestamp = doc.get("timestamp", datetime.utcnow())
                bucket = self._get_time_bucket(timestamp)
                bucket_key = f"{segment_id}_{bucket.isoformat()}"
                
                if bucket_key not in segments_dict:
                    segments_dict[bucket_key] = {
                        "segment_id": segment_id,
                        "timestamp_bucket": bucket,
                        "speeds": [],
                        "incidents": [],
                        "roadwork": False,
                        "lat": doc.get("latitude", 0.0),
                        "lon": doc.get("longitude", 0.0),
                        "segment_name": doc.get("segment_name", ""),
                        "sources": set()
                    }
                
                seg = segments_dict[bucket_key]
                if doc.get("speed_mph"):
                    seg["speeds"].append(doc.get("speed_mph"))
                if doc.get("incident_type"):
                    seg["incidents"].append(doc.get("incident_type"))
                if doc.get("roadwork_flag"):
                    seg["roadwork"] = True
                seg["sources"].add("511ny")
            
            # Process DOT data
            for doc in traffic_dot:
                segment_id = doc.get("segment_id")
                if not segment_id:
                    continue
                
                timestamp = doc.get("timestamp", datetime.utcnow())
                bucket = self._get_time_bucket(timestamp)
                bucket_key = f"{segment_id}_{bucket.isoformat()}"
                
                if bucket_key not in segments_dict:
                    segments_dict[bucket_key] = {
                        "segment_id": segment_id,
                        "timestamp_bucket": bucket,
                        "speeds": [],
                        "incidents": [],
                        "roadwork": False,
                        "lat": doc.get("latitude", 0.0),
                        "lon": doc.get("longitude", 0.0),
                        "segment_name": "",
                        "sources": set()
                    }
                
                seg = segments_dict[bucket_key]
                if doc.get("speed_mph"):
                    seg["speeds"].append(doc.get("speed_mph"))
                seg["sources"].add("nyc_dot_opendata")
            
            # Create segments_state documents
            segments_to_insert = []
            
            for bucket_key, seg_data in segments_dict.items():
                # Validate and impute coordinates
                valid_lat, valid_lon = await self._validate_and_impute_coordinates(
                    seg_data["segment_id"],
                    seg_data.get("lat"),
                    seg_data.get("lon")
                )
                
                # Calculate average speed
                speeds = seg_data["speeds"]
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                else:
                    # Impute missing speed
                    avg_speed = await self.imputation_service.impute_missing_speed(
                        seg_data["segment_id"],
                        seg_data["timestamp_bucket"],
                        None
                    )
                
                # Clean speed
                cleaned_speed = self.imputation_service.clean_speed_value(
                    avg_speed,
                    seg_data["segment_id"]
                )
                
                if cleaned_speed is None:
                    cleaned_speed = await self.imputation_service.impute_missing_speed(
                        seg_data["segment_id"],
                        seg_data["timestamp_bucket"],
                        None
                    )
                
                # Calculate congestion index
                congestion_index = self.imputation_service.calculate_congestion_index(cleaned_speed)
                
                # Check for incidents
                incident_flag = len(seg_data["incidents"]) > 0 or seg_data["roadwork"]
                
                # Check for transit delays nearby (use validated coordinates)
                transit_delay_flag = await self.correlation_service.check_transit_delays_nearby(
                    valid_lat,
                    valid_lon,
                    seg_data["timestamp_bucket"]
                )
                
                # Find nearby air quality (use validated coordinates)
                pm25_nearby = await self.correlation_service.find_nearby_air_quality(
                    valid_lat,
                    valid_lon,
                    seg_data["timestamp_bucket"]
                )
                
                # Calculate confidence score
                confidence = self.imputation_service.calculate_confidence_score(
                    has_traffic_data=len(speeds) > 0,
                    has_transit_data=transit_delay_flag,
                    has_air_quality=pm25_nearby is not None,
                    speed_quality="good" if speeds else "imputed"
                )
                
                # Determine borough from coordinates
                borough = self._get_borough_from_coordinates(valid_lat, valid_lon)
                
                # Create segment document with validated coordinates
                segment_doc = {
                    "segment_id": seg_data["segment_id"],
                    "timestamp_bucket": seg_data["timestamp_bucket"],
                    "speed_mph": cleaned_speed,
                    "congestion_index": congestion_index,
                    "incident_flag": incident_flag,
                    "transit_delay_flag": transit_delay_flag,
                    "pm25_nearby": pm25_nearby,
                    "data_confidence_score": confidence,
                    "latitude": valid_lat,
                    "longitude": valid_lon,
                    "segment_name": seg_data["segment_name"],
                    "sources": list(seg_data["sources"]),
                    "borough": borough
                }
                
                segments_to_insert.append(segment_doc)
            
            # Insert or update segments_state
            inserted_count = 0
            for seg_doc in segments_to_insert:
                # Use upsert to avoid duplicates
                result = await self.db.segments_state.update_one(
                    {
                        "segment_id": seg_doc["segment_id"],
                        "timestamp_bucket": seg_doc["timestamp_bucket"]
                    },
                    {"$set": seg_doc},
                    upsert=True
                )
                if result.upserted_id or result.modified_count > 0:
                    inserted_count += 1
            
            logger.info(f"Created/updated {inserted_count} segments_state records")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error processing traffic data: {e}", exc_info=True)
            return 0
    
    async def _process_zones(self, cutoff_time: datetime) -> int:
        """Aggregate segments into zones"""
        try:
            # Get recent segments
            segments = await self.db.segments_state.find({
                "timestamp_bucket": {"$gte": cutoff_time}
            }).to_list(length=1000)
            
            if not segments:
                return 0
            
            # Define zones (simplified - in production, use proper geographic boundaries)
            zones_dict = defaultdict(lambda: {
                "speeds": [],
                "congestion_indices": [],
                "pm25_values": [],
                "incident_count": 0,
                "transit_delay_count": 0,
                "segment_count": 0,
                "latitudes": [],
                "longitudes": []
            })
            
            # Group segments by zone (simplified: use bounding box approach)
            for seg in segments:
                lat = seg.get("latitude")
                lon = seg.get("longitude")
                
                # Skip segments with invalid coordinates
                if not self._is_valid_coordinate(lat, lon):
                    continue
                
                # Determine borough and create zone_id
                borough = self._get_borough_from_coordinates(lat, lon)
                
                # Simple zone assignment based on coordinates
                # In production, use proper zone boundaries
                if 40.7 <= lat <= 40.8 and -74.05 <= lon <= -73.95:
                    zone_id = "manhattan_cbd"
                elif 40.65 <= lat <= 40.75 and -74.05 <= lon <= -73.9:
                    zone_id = "brooklyn_downtown"
                elif 40.7 <= lat <= 40.8 and -73.95 <= lon <= -73.8:
                    zone_id = "queens_midtown"
                else:
                    # Create zone_id based on borough
                    zone_id = f"{borough.lower().replace(' ', '_')}_zone"
                
                zone = zones_dict[zone_id]
                zone["speeds"].append(seg.get("speed_mph", 0))
                zone["congestion_indices"].append(seg.get("congestion_index", 0))
                if seg.get("pm25_nearby"):
                    zone["pm25_values"].append(seg.get("pm25_nearby"))
                if seg.get("incident_flag"):
                    zone["incident_count"] += 1
                if seg.get("transit_delay_flag"):
                    zone["transit_delay_count"] += 1
                zone["segment_count"] += 1
                zone["latitudes"].append(lat)
                zone["longitudes"].append(lon)
            
            # Create zone documents
            zones_to_insert = []
            timestamp_bucket = self._get_time_bucket(datetime.utcnow())
            
            for zone_id, zone_data in zones_dict.items():
                if zone_data["segment_count"] == 0:
                    continue
                
                avg_speed = sum(zone_data["speeds"]) / len(zone_data["speeds"])
                avg_congestion = sum(zone_data["congestion_indices"]) / len(zone_data["congestion_indices"])
                avg_pm25 = None
                if zone_data["pm25_values"]:
                    avg_pm25 = sum(zone_data["pm25_values"]) / len(zone_data["pm25_values"])
                
                # Calculate pollution risk
                traffic_pollution_risk = self.correlation_service.calculate_traffic_pollution_risk(
                    avg_congestion,
                    avg_pm25
                )
                
                # Calculate bounding box (only use valid coordinate pairs)
                # We already filtered invalid coordinates when grouping, so use all available
                if not zone_data["latitudes"] or not zone_data["longitudes"]:
                    # Skip zones with no coordinates
                    continue
                
                min_lat = min(zone_data["latitudes"])
                max_lat = max(zone_data["latitudes"])
                min_lon = min(zone_data["longitudes"])
                max_lon = max(zone_data["longitudes"])
                
                # Determine borough from zone_id or coordinates
                borough = "Manhattan"  # default
                if "manhattan" in zone_id.lower():
                    borough = "Manhattan"
                elif "brooklyn" in zone_id.lower() or "bk" in zone_id.lower():
                    borough = "Brooklyn"
                elif "queens" in zone_id.lower() or "qn" in zone_id.lower():
                    borough = "Queens"
                elif "bronx" in zone_id.lower() or "bx" in zone_id.lower():
                    borough = "Bronx"
                elif "staten" in zone_id.lower() or "si" in zone_id.lower():
                    borough = "Staten Island"
                elif valid_lats and valid_lons:
                    # Use center of bounding box to determine borough
                    center_lat = (min_lat + max_lat) / 2
                    center_lon = (min_lon + max_lon) / 2
                    borough = self._get_borough_from_coordinates(center_lat, center_lon)
                
                zone_doc = {
                    "zone_id": zone_id,
                    "timestamp_bucket": timestamp_bucket,
                    "avg_speed_mph": avg_speed,
                    "avg_congestion_index": avg_congestion,
                    "avg_pm25": avg_pm25,
                    "traffic_pollution_risk": traffic_pollution_risk,
                    "segment_count": zone_data["segment_count"],
                    "incident_count": zone_data["incident_count"],
                    "transit_delay_count": zone_data["transit_delay_count"],
                    "borough": borough,
                    "bounding_box": {
                        "min_lat": min_lat,
                        "max_lat": max_lat,
                        "min_lon": min_lon,
                        "max_lon": max_lon
                    }
                }
                
                zones_to_insert.append(zone_doc)
            
            # Insert or update zones_state
            inserted_count = 0
            for zone_doc in zones_to_insert:
                result = await self.db.zones_state.update_one(
                    {
                        "zone_id": zone_doc["zone_id"],
                        "timestamp_bucket": zone_doc["timestamp_bucket"]
                    },
                    {"$set": zone_doc},
                    upsert=True
                )
                if result.upserted_id or result.modified_count > 0:
                    inserted_count += 1
            
            logger.info(f"Created/updated {inserted_count} zones_state records")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error processing zones: {e}", exc_info=True)
            return 0
    
    def _get_time_bucket(self, timestamp: datetime) -> datetime:
        """Round timestamp to 5-minute bucket"""
        minutes = (timestamp.minute // self.bucket_minutes) * self.bucket_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)

