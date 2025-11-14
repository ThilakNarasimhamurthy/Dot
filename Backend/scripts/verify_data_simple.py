#!/usr/bin/env python3
"""
Simple verification tool - Shows the ACTUAL raw data stored in your database
This is what NYC DOT API sent, before any transformation
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection, get_database

async def show_raw_data():
    """Show the actual raw data from NYC DOT that's stored in MongoDB"""
    await connect_to_mongo()
    db = get_database()
    
    print("=" * 80)
    print("🔍 VERIFICATION: What NYC DOT Data is Actually Stored?")
    print("=" * 80)
    print()
    
    # Get raw NYC DOT data (before transformation)
    print("📦 RAW NYC DOT DATA (Direct from API, stored in MongoDB)")
    print("-" * 80)
    raw_dot = await db.raw_traffic_dot.find({}).sort("created_at", -1).limit(5).to_list(length=5)
    
    if not raw_dot:
        print("⚠️  No raw NYC DOT data found in database")
        print("   This means either:")
        print("   1. USE_MOCKS=true (using fake data)")
        print("   2. No data has been ingested yet")
        print("   3. NYC DOT API calls failed")
    else:
        for i, doc in enumerate(raw_dot, 1):
            print(f"\n{i}. Raw Record from NYC DOT API:")
            print(f"   Stored at: {doc.get('created_at', 'N/A')}")
            
            # Show the actual data structure
            data = doc.get('data', {})
            if isinstance(data, dict):
                # Show key fields
                print(f"   Location ID: {data.get('id', data.get('link_id', data.get('segment_id', 'Unknown')))}")
                print(f"   Speed: {data.get('speed', data.get('speed_mph', 'N/A'))} mph")
                print(f"   Data As Of: {data.get('data_as_of', data.get('timestamp', 'N/A'))}")
                if 'latitude' in data or 'lat' in data:
                    lat = data.get('latitude') or data.get('lat')
                    lon = data.get('longitude') or data.get('lon')
                    print(f"   Location: {lat}, {lon}")
            else:
                print(f"   Raw data: {str(data)[:100]}...")
    
    print()
    print("=" * 80)
    print("🔄 TRANSFORMED DATA (What Dashboard Shows)")
    print("-" * 80)
    
    # Get processed segments (what dashboard shows)
    segments = await db.segments_state.find({}).sort("timestamp_bucket", -1).limit(5).to_list(length=5)
    
    if not segments:
        print("⚠️  No processed segments found")
    else:
        for i, seg in enumerate(segments, 1):
            print(f"\n{i}. Dashboard Segment:")
            print(f"   Segment ID: {seg.get('segment_id', 'Unknown')}")
            print(f"   Speed: {seg.get('speed_mph', 'N/A')} mph")
            print(f"   Congestion: {seg.get('congestion_index', 0) * 100:.0f}%")
            print(f"   Timestamp: {seg.get('timestamp_bucket', 'N/A')}")
            print(f"   Sources: {', '.join(seg.get('sources', []))}")
    
    print()
    print("=" * 80)
    print("💡 HOW TO VERIFY")
    print("=" * 80)
    print()
    print("1. Check 'Raw NYC DOT Data' above - this is what came from the API")
    print("2. Check 'Dashboard Segment' - this is the transformed version")
    print("3. Compare SPEEDS - they should be similar if using real data")
    print("4. Compare TIMESTAMPS - should be recent (within last hour)")
    print()
    print("⚠️  Note: Location IDs will be different because:")
    print("   - NYC DOT uses: numeric IDs (159, 376, etc.)")
    print("   - Dashboard creates: named IDs (dot_seg_001, 511_seg_001, etc.)")
    print("   - This is NORMAL - the system transforms the data")
    print()
    
    # Check if using mocks
    from app.config import settings
    print(f"Current mode: {'🔴 MOCK DATA' if settings.use_mocks else '✅ REAL DATA'}")
    if settings.use_mocks:
        print("   ⚠️  Dashboard is using fake/mock data")
        print("   ⚠️  It won't match NYC DOT API")
        print("   💡 Set USE_MOCKS=false in .env to use real data")
    else:
        print("   ✅ Dashboard should match NYC DOT API speeds")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(show_raw_data())

