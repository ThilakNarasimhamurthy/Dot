#!/usr/bin/env python3
"""
Test script for live data ingestion
Tests real API endpoints (not mocks) to verify data collection
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection
from app.agents.agent1_ingestion import IngestionAgent
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_live_ingestion():
    """Test live data ingestion from real APIs"""
    print("=" * 80)
    print("LIVE DATA INGESTION TEST")
    print("=" * 80)
    print(f"Start time: {datetime.utcnow()}\n")
    
    # Check if using mocks
    if settings.use_mocks:
        print("⚠️  WARNING: USE_MOCKS=true in config")
        print("   Set USE_MOCKS=false in .env to test real APIs\n")
        print("⚠️  Skipping - USE_MOCKS is true. Set USE_MOCKS=false to test real APIs.")
        return
    
    try:
        # Connect to MongoDB
        print("Step 1: Connecting to MongoDB...")
        await connect_to_mongo()
        print("✓ Connected to MongoDB\n")
        
        # Run ingestion
        print("Step 2: Running Data Ingestion Agent...")
        print("   Fetching data from all sources...\n")
        
        ingestion_agent = IngestionAgent()
        results = await ingestion_agent.ingest_all_sources()
        
        print("=" * 80)
        print("INGESTION RESULTS:")
        print("=" * 80)
        print(f"  511NY Traffic:      {results.get('traffic_511', 0):>4} records")
        print(f"  NYC DOT Traffic:    {results.get('traffic_dot', 0):>4} records")
        print(f"  MTA Transit:        {results.get('transit_mta', 0):>4} records")
        print(f"  Air Quality:        {results.get('air_quality', 0):>4} records")
        print()
        
        total = sum(results.values())
        print(f"  TOTAL:              {total:>4} records\n")
        
        # Verify data in MongoDB
        print("Step 3: Verifying data in MongoDB...")
        db = ingestion_agent.db
        
        collections = {
            "raw_traffic_511": "511NY Traffic",
            "raw_traffic_dot": "NYC DOT Traffic",
            "raw_transit_mta": "MTA Transit",
            "raw_air_quality": "Air Quality"
        }
        
        for collection_name, display_name in collections.items():
            count = await db[collection_name].count_documents({})
            latest = await db[collection_name].find_one({}, sort=[("timestamp", -1)])
            
            if latest:
                latest_time = latest.get("timestamp", "Unknown")
                print(f"  {display_name:20} {count:>4} total records, latest: {latest_time}")
            else:
                print(f"  {display_name:20} {count:>4} total records, no recent data")
        
        print()
        
        # Summary
        if total > 0:
            print("=" * 80)
            print("✅ INGESTION TEST PASSED")
            print("=" * 80)
            print(f"\n✓ Successfully ingested {total} records from {len([r for r in results.values() if r > 0])} sources")
            print("✓ Data stored in MongoDB")
            print("\nNext steps:")
            print("  1. Run cleaning agent: python scripts/run_simulation.py")
            print("  2. Check API endpoints: http://localhost:8000/api/segments/current")
        else:
            print("=" * 80)
            print("⚠️  INGESTION TEST - NO DATA RECEIVED")
            print("=" * 80)
            print("\nPossible issues:")
            print("  - API endpoints may be incorrect")
            print("  - API keys may be missing or invalid")
            print("  - Network connectivity issues")
            print("  - APIs may be rate-limited")
            print("\nCheck logs above for specific errors.")
        
        print()
        
    except Exception as e:
        logger.error(f"Ingestion test error: {e}", exc_info=True)
        print(f"\n❌ Error during ingestion test: {e}\n")
    
    finally:
        await close_mongo_connection()
        print("✓ MongoDB connection closed")


if __name__ == "__main__":
    asyncio.run(test_live_ingestion())

