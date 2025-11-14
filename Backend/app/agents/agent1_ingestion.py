"""
Agent 1: Data Ingestion Agent
Pulls live feeds reliably on a schedule and stores RAW data in MongoDB
"""
import logging
from datetime import datetime
from typing import List, Dict
from app.database import get_database
from app.clients.traffic_511 import Traffic511Client
from app.clients.traffic_dot import TrafficDOTClient
from app.clients.transit_mta import TransitMTAClient
from app.clients.air_quality import AirQualityClient

logger = logging.getLogger(__name__)


class IngestionAgent:
    """Agent responsible for ingesting raw data from all sources"""
    
    def __init__(self):
        self.traffic_511_client = Traffic511Client()
        self.traffic_dot_client = TrafficDOTClient()
        self.transit_mta_client = TransitMTAClient()
        self.air_quality_client = AirQualityClient()
        self.db = get_database()
    
    async def _store_ingestion_status(self, source: str, record_count: int, timestamp: datetime, status: str, error: str = None):
        """Store ingestion status for tracking"""
        try:
            status_doc = {
                "source": source,
                "record_count": record_count,
                "timestamp": timestamp,
                "status": status,
                "error": error
            }
            await self.db.ingestion_status.insert_one(status_doc)
        except Exception as e:
            logger.warning(f"Failed to store ingestion status: {e}")
    
    async def ingest_all_sources(self) -> Dict[str, int]:
        """
        Ingest data from all sources and store in MongoDB
        
        Returns:
            Dictionary with counts of ingested records per source
        """
        results = {
            "traffic_511": 0,
            "traffic_dot": 0,
            "transit_mta": 0,
            "air_quality": 0
        }
        
        ingestion_start = datetime.utcnow()
        
        try:
            # Ingest 511NY Traffic
            results["traffic_511"] = await self._ingest_traffic_511()
            
            # Ingest NYC DOT Traffic
            results["traffic_dot"] = await self._ingest_traffic_dot()
            
            # Ingest MTA Transit
            results["transit_mta"] = await self._ingest_transit_mta()
            
            # Ingest Air Quality
            results["air_quality"] = await self._ingest_air_quality()
            
            # Store overall ingestion status
            total_records = sum(results.values())
            await self._store_ingestion_status(
                "all_sources",
                total_records,
                ingestion_start,
                "success" if total_records > 0 else "partial"
            )
            
            logger.info(f"Ingestion complete: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during ingestion: {e}", exc_info=True)
            await self._store_ingestion_status("all_sources", 0, ingestion_start, "failed", str(e))
            return results
    
    async def _ingest_traffic_511(self) -> int:
        """Ingest traffic data from 511NY API"""
        try:
            data = await self.traffic_511_client.fetch_traffic_data()
            
            if not data:
                logger.warning("No data received from 511NY")
                return 0
            
            # Prepare documents for MongoDB
            documents = []
            for item in data:
                doc = {
                    "timestamp": item.get("timestamp", datetime.utcnow()),
                    "source": "511ny",
                    "segment_id": item.get("segment_id"),
                    "segment_name": item.get("segment_name", ""),
                    "speed_mph": item.get("speed_mph", 0.0),
                    "incident_type": item.get("incident_type"),
                    "incident_description": item.get("incident_description"),
                    "roadwork_flag": item.get("roadwork_flag", False),
                    "camera_id": item.get("camera_id"),
                    "latitude": item.get("latitude", 0.0),
                    "longitude": item.get("longitude", 0.0),
                    "raw_data": item  # Store full response
                }
                documents.append(doc)
            
            # Insert into MongoDB
            if documents:
                result = await self.db.raw_traffic_511.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} records into raw_traffic_511")
                
                # Store ingestion status
                ingestion_time = datetime.utcnow()
                await self._store_ingestion_status("traffic_511", len(result.inserted_ids), ingestion_time, "success")
                
                return len(result.inserted_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error ingesting 511NY data: {e}", exc_info=True)
            await self._store_ingestion_status("traffic_511", 0, datetime.utcnow(), "failed", str(e))
            return 0
    
    async def _ingest_traffic_dot(self) -> int:
        """Ingest traffic data from NYC DOT OpenData"""
        try:
            data = await self.traffic_dot_client.fetch_traffic_speeds()
            
            if not data:
                logger.warning("No data received from NYC DOT")
                return 0
            
            documents = []
            ingestion_time = datetime.utcnow()
            for item in data:
                doc = {
                    "timestamp": item.get("timestamp", ingestion_time),
                    "created_at": ingestion_time,  # Track when ingested
                    "source": "nyc_dot_opendata",
                    "segment_id": item.get("segment_id"),
                    "speed_mph": item.get("speed_mph", 0.0),
                    "latitude": item.get("latitude", 0.0),
                    "longitude": item.get("longitude", 0.0),
                    "raw_data": item
                }
                documents.append(doc)
            
            if documents:
                result = await self.db.raw_traffic_dot.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} records into raw_traffic_dot")
                
                # Store ingestion status
                await self._store_ingestion_status("traffic_dot", len(result.inserted_ids), ingestion_time, "success")
                
                return len(result.inserted_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error ingesting NYC DOT data: {e}", exc_info=True)
            await self._store_ingestion_status("traffic_dot", 0, datetime.utcnow(), "failed", str(e))
            return 0
    
    async def _ingest_transit_mta(self) -> int:
        """Ingest transit data from MTA GTFS-RT"""
        try:
            data = await self.transit_mta_client.fetch_transit_data()
            
            if not data:
                logger.warning("No data received from MTA")
                return 0
            
            documents = []
            for item in data:
                doc = {
                    "timestamp": item.get("timestamp", datetime.utcnow()),
                    "source": "mta_gtfs_rt",
                    "trip_id": item.get("trip_id"),
                    "route_id": item.get("route_id"),
                    "vehicle_id": item.get("vehicle_id"),
                    "stop_id": item.get("stop_id"),
                    "delay_seconds": item.get("delay_seconds", 0),
                    "arrival_time": item.get("arrival_time"),
                    "departure_time": item.get("departure_time"),
                    "latitude": item.get("latitude", 0.0),
                    "longitude": item.get("longitude", 0.0),
                    "raw_data": item
                }
                documents.append(doc)
            
            if documents:
                result = await self.db.raw_transit_mta.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} records into raw_transit_mta")
                return len(result.inserted_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error ingesting MTA data: {e}", exc_info=True)
            return 0
    
    async def _ingest_air_quality(self) -> int:
        """Ingest air quality data"""
        try:
            data = await self.air_quality_client.fetch_air_quality_data()
            
            if not data:
                logger.warning("No data received from Air Quality API")
                return 0
            
            documents = []
            for item in data:
                doc = {
                    "timestamp": item.get("timestamp", datetime.utcnow()),
                    "source": item.get("source", "dohmn"),
                    "sensor_id": item.get("sensor_id"),
                    "pm25": item.get("pm25", 0.0),
                    "pm10": item.get("pm10"),
                    "aqi": item.get("aqi"),
                    "latitude": item.get("latitude", 0.0),
                    "longitude": item.get("longitude", 0.0),
                    "raw_data": item
                }
                documents.append(doc)
            
            if documents:
                result = await self.db.raw_air_quality.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} records into raw_air_quality")
                return len(result.inserted_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error ingesting Air Quality data: {e}", exc_info=True)
            return 0

