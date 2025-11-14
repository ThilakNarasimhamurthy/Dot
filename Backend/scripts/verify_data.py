#!/usr/bin/env python3
"""
Simple tool to verify dashboard data against NYC DOT API
Shows side-by-side comparison in readable format
"""
import asyncio
import sys
import os
from datetime import datetime
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.config import settings

async def fetch_nyc_dot_data():
    """Fetch real data from NYC DOT API"""
    url = settings.nyc_dot_traffic_speeds_url
    params = {
        "$limit": 10,
        "$order": "data_as_of DESC"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"❌ Error fetching NYC DOT data: {e}")
        return []

async def fetch_dashboard_data():
    """Fetch data from our dashboard database"""
    await connect_to_mongo()
    db = get_database()
    
    # Get most recent segments
    segments = await db.segments_state.find({}).sort("timestamp_bucket", -1).limit(10).to_list(length=10)
    
    await close_mongo_connection()
    return segments

def format_segment_for_display(seg, source="Dashboard"):
    """Format segment data for readable display"""
    if source == "NYC DOT":
        # NYC DOT format
        speed = seg.get("speed", seg.get("speed_mph", "N/A"))
        location = seg.get("id", seg.get("segment_id", "Unknown"))
        timestamp = seg.get("data_as_of", seg.get("timestamp", "N/A"))
        
        return {
            "location": str(location)[:30],
            "speed": f"{speed} mph" if isinstance(speed, (int, float)) else str(speed),
            "timestamp": str(timestamp)[:19] if timestamp else "N/A",
            "source": "NYC DOT API"
        }
    else:
        # Dashboard format
        return {
            "location": seg.get("segment_id", "Unknown"),
            "speed": f"{seg.get('speed_mph', 'N/A')} mph",
            "congestion": f"{seg.get('congestion_index', 0) * 100:.0f}%",
            "incident": "⚠️ Yes" if seg.get("incident_flag") else "✅ No",
            "timestamp": str(seg.get("timestamp_bucket", "N/A"))[:19] if seg.get("timestamp_bucket") else "N/A",
            "source": "Dashboard DB"
        }

async def main():
    print("=" * 80)
    print("🔍 DATA VERIFICATION TOOL")
    print("=" * 80)
    print()
    print("Comparing Dashboard data with NYC DOT API...")
    print()
    
    # Fetch from both sources
    print("📡 Fetching NYC DOT API data...")
    nyc_dot_data = await fetch_nyc_dot_data()
    print(f"   ✅ Got {len(nyc_dot_data)} records from NYC DOT")
    print()
    
    print("📊 Fetching Dashboard database data...")
    dashboard_data = await fetch_dashboard_data()
    print(f"   ✅ Got {len(dashboard_data)} records from Dashboard")
    print()
    
    print("=" * 80)
    print("📋 NYC DOT API DATA (Real Source)")
    print("=" * 80)
    print()
    
    if not nyc_dot_data:
        print("⚠️  No data from NYC DOT API")
    else:
        for i, item in enumerate(nyc_dot_data[:5], 1):
            speed = item.get("speed", item.get("speed_mph", "N/A"))
            location = item.get("id", item.get("segment_id", item.get("link_id", "Unknown")))
            timestamp = item.get("data_as_of", item.get("timestamp", "N/A"))
            
            print(f"{i}. Location: {location}")
            print(f"   Speed: {speed} mph" if isinstance(speed, (int, float)) else f"   Speed: {speed}")
            print(f"   Timestamp: {timestamp}")
            print()
    
    print("=" * 80)
    print("🖥️  DASHBOARD DATA (What You See)")
    print("=" * 80)
    print()
    
    if not dashboard_data:
        print("⚠️  No data in Dashboard database")
    else:
        for i, seg in enumerate(dashboard_data[:5], 1):
            location = seg.get("segment_id", "Unknown")
            speed = seg.get("speed_mph", "N/A")
            congestion = seg.get("congestion_index", 0)
            incident = seg.get("incident_flag", False)
            timestamp = seg.get("timestamp_bucket", "N/A")
            
            print(f"{i}. Location: {location}")
            print(f"   Speed: {speed} mph")
            print(f"   Congestion: {congestion * 100:.0f}%")
            print(f"   Incident: {'⚠️ Yes' if incident else '✅ No'}")
            print(f"   Timestamp: {timestamp}")
            print()
    
    print("=" * 80)
    print("💡 VERIFICATION TIPS")
    print("=" * 80)
    print()
    print("1. Check if speeds are similar (within 5-10 mph)")
    print("2. Check if timestamps are recent (within last hour)")
    print("3. If USE_MOCKS=true, dashboard shows fake data")
    print("4. If USE_MOCKS=false, dashboard should match NYC DOT")
    print()
    print(f"Current USE_MOCKS setting: {settings.use_mocks}")
    if settings.use_mocks:
        print("⚠️  Using MOCK data - Dashboard won't match NYC DOT API")
    else:
        print("✅ Using REAL data - Dashboard should match NYC DOT API")
    print()

if __name__ == "__main__":
    asyncio.run(main())

