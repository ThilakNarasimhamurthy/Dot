"""
MongoDB database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager"""
    
    client: Optional[AsyncIOMotorClient] = None
    database = None


# Global database instance
db = Database()


async def connect_to_mongo():
    """Connect to MongoDB (optional - API will still start if connection fails)"""
    try:
        # MongoDB Atlas (mongodb+srv://) handles SSL automatically
        # For local MongoDB, no SSL needed
        # Motor/PyMongo handles SSL for Atlas connections automatically
        
        # MongoDB Atlas connection string includes SSL/TLS automatically
        # For mongodb+srv://, SSL is required and handled automatically
        db.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=10000,  # 10 second timeout for Atlas
            tlsAllowInvalidCertificates=False  # Use proper SSL certificates
        )
        db.database = db.client[settings.mongodb_db_name]
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        error_msg = str(e)
        if "SSL" in error_msg or "TLS" in error_msg:
            logger.warning(f"MongoDB SSL connection failed. Common issues:")
            logger.warning("  1. Your IP address may not be whitelisted in MongoDB Atlas")
            logger.warning("  2. Go to MongoDB Atlas → Network Access → Add IP Address")
            logger.warning("  3. Add '0.0.0.0/0' to allow all IPs (for testing only)")
        elif "authentication" in error_msg.lower():
            logger.warning(f"MongoDB authentication failed. Check username/password in connection string.")
        else:
            logger.warning(f"Failed to connect to MongoDB: {e}")
            logger.warning("API will continue without database. Some endpoints may return empty data.")
        # Don't raise - allow API to start without MongoDB
        db.client = None
        db.database = None


async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed")


async def create_indexes():
    """Create database indexes for optimal query performance"""
    if db.database is None:
        logger.warning("Database not connected, skipping index creation")
        return
    
    try:
        # segments_state indexes
        segments_collection = db.database.segments_state
        await segments_collection.create_index([("segment_id", 1), ("timestamp_bucket", -1)])
        await segments_collection.create_index([("timestamp_bucket", -1)])
        
        # zones_state indexes
        zones_collection = db.database.zones_state
        await zones_collection.create_index([("zone_id", 1), ("timestamp_bucket", -1)])
        await zones_collection.create_index([("timestamp_bucket", -1)])
        
        # predicted_segments indexes
        predictions_collection = db.database.predicted_segments
        await predictions_collection.create_index([("segment_id", 1), ("target_timestamp", -1)])
        await predictions_collection.create_index([("target_timestamp", 1)])
        
        # Raw collections indexes
        raw_traffic_511 = db.database.raw_traffic_511
        await raw_traffic_511.create_index([("timestamp", -1)])
        await raw_traffic_511.create_index([("segment_id", 1)])
        
        raw_transit_mta = db.database.raw_transit_mta
        await raw_transit_mta.create_index([("timestamp", -1)])
        await raw_transit_mta.create_index([("route_id", 1)])
        
        raw_air_quality = db.database.raw_air_quality
        await raw_air_quality.create_index([("timestamp", -1)])
        await raw_air_quality.create_index([("sensor_id", 1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Failed to create some indexes: {e}")


def get_database():
    """Get database instance"""
    return db.database

