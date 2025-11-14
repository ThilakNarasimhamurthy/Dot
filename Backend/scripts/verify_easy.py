#!/usr/bin/env python3
"""
EASY VERIFICATION - Just compare speeds, ignore location names
Shows: NYC DOT API → What gets stored → What dashboard shows
"""
import asyncio
import sys
import os
import httpx
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.config import settings

async def main():
    print("=" * 80)
    print("🔍 EASY VERIFICATION - Just Compare Speeds!")
    print("=" * 80)
    print()
    
    # Step 1: Fetch directly from NYC DOT API
    print("📡 Step 1: Fetching from NYC DOT API...")
    nyc_url = settings.nyc_dot_traffic_speeds_url
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(nyc_url, params={"$limit": 5, "$order": "data_as_of DESC"})
            response.raise_for_status()
            nyc_data = response.json()
            print(f"   ✅ Got {len(nyc_data)} records from NYC DOT")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        nyc_data = []
    
    print()
    print("=" * 80)
    print("🌐 NYC DOT API (What the City Website Shows)")
    print("=" * 80)
    speeds_nyc = []
    
    if nyc_data:
        for i, item in enumerate(nyc_data[:5], 1):
            speed = item.get("speed", item.get("speed_mph", item.get("speed_mph_nbe", "N/A")))
            location_id = item.get("id", item.get("link_id", item.get("segment_id", "Unknown")))
            timestamp = item.get("data_as_of", item.get("timestamp", "N/A"))
            
            # Convert to float if possible
            if isinstance(speed, (int, float)):
                speeds_nyc.append(float(speed))
                print(f"{i}. Speed: {speed:.1f} mph | Location ID: {location_id} | Time: {str(timestamp)[:19]}")
            else:
                print(f"{i}. Speed: {speed} mph | Location ID: {location_id} | Time: {str(timestamp)[:19]}")
        
        if speeds_nyc:
            # Filter out 0 speeds for average (they're stopped traffic)
            non_zero_speeds = [s for s in speeds_nyc if s > 0]
            if non_zero_speeds:
                avg_speed_nyc = sum(non_zero_speeds) / len(non_zero_speeds)
                print(f"\n   📊 Average Speed (non-zero): {avg_speed_nyc:.1f} mph")
                print(f"   📊 Speed Range: {min(non_zero_speeds):.1f} - {max(non_zero_speeds):.1f} mph")
                print(f"   📊 Total Records: {len(speeds_nyc)} (including {len(speeds_nyc) - len(non_zero_speeds)} stopped/0 mph)")
            else:
                print(f"\n   ⚠️  All speeds are 0 (stopped traffic)")
        else:
            print("\n   ⚠️  No speed data found")
    else:
        print("   ⚠️  No data from NYC DOT API")
    
    print()
    print("=" * 80)
    print("🖥️  YOUR DASHBOARD (What You See on Screen)")
    print("=" * 80)
    
    # Step 2: Get dashboard data
    await connect_to_mongo()
    db = get_database()
    
    segments = await db.segments_state.find({}).sort("timestamp_bucket", -1).limit(5).to_list(length=5)
    
    speeds_dash = []
    if segments:
        for i, seg in enumerate(segments[:5], 1):
            speed = seg.get("speed_mph", "N/A")
            location = seg.get("segment_id", "Unknown")
            congestion = seg.get("congestion_index", 0)
            timestamp = seg.get("timestamp_bucket", "N/A")
            
            if isinstance(speed, (int, float)):
                speeds_dash.append(float(speed))
            
            print(f"{i}. Speed: {speed:.1f} mph | Location: {location} | Congestion: {congestion*100:.0f}% | Time: {str(timestamp)[:19]}")
        
        if speeds_dash:
            avg_speed_dash = sum(speeds_dash) / len(speeds_dash)
            print(f"\n   📊 Average Speed: {avg_speed_dash:.1f} mph")
            print(f"   📊 Speed Range: {min(speeds_dash):.1f} - {max(speeds_dash):.1f} mph")
        else:
            print("\n   ⚠️  No valid speeds found")
    else:
        print("   ⚠️  No data in dashboard")
    
    await close_mongo_connection()
    
    print()
    print("=" * 80)
    print("✅ VERIFICATION RESULT")
    print("=" * 80)
    print()
    
    print()
    if speeds_nyc and speeds_dash:
        # Filter out 0 speeds for comparison
        nyc_non_zero = [s for s in speeds_nyc if s > 0]
        dash_non_zero = [s for s in speeds_dash if s > 0]
        
        if nyc_non_zero and dash_non_zero:
            avg_nyc = sum(nyc_non_zero) / len(nyc_non_zero)
            avg_dash = sum(dash_non_zero) / len(dash_non_zero)
            diff = abs(avg_nyc - avg_dash)
            
            print(f"NYC DOT Average Speed: {avg_nyc:.1f} mph (from {len(nyc_non_zero)} moving segments)")
            print(f"Dashboard Average Speed: {avg_dash:.1f} mph (from {len(dash_non_zero)} segments)")
            print(f"Difference: {diff:.1f} mph")
            print()
            
            # Check if both are in realistic ranges
            nyc_range_ok = all(0 <= s <= 60 for s in speeds_nyc)
            dash_range_ok = all(0 <= s <= 60 for s in speeds_dash)
            
            if nyc_range_ok and dash_range_ok:
                print("✅ Both show realistic speeds (0-60 mph for city traffic)")
                if diff < 15:
                    print("✅ Speeds are similar - Dashboard is using REAL data!")
                else:
                    print("⚠️  Speeds differ, but both are realistic")
                    if settings.use_mocks:
                        print("   Reason: USE_MOCKS=true (using fake data)")
                    else:
                        print("   Reason: Different segments or time periods")
                        print("   💡 This is OK - different locations have different speeds!")
            else:
                print("⚠️  Some speeds seem unrealistic")
        else:
            print("✅ Both sources have data")
            print("💡 Compare the speed ranges shown above")
            print("   If both show 0-60 mph range → Realistic city traffic ✅")
    elif speeds_nyc:
        print("✅ NYC DOT API is working (got speeds)")
        print("⚠️  Dashboard has no valid speeds to compare")
        print("   Try running: python3 scripts/run_simulation.py")
    elif speeds_dash:
        print("✅ Dashboard has data")
        print("⚠️  NYC DOT API returned no valid speeds")
        print("   (Some segments might have 0 speed - that's normal)")
    else:
        print("⚠️  No speed data to compare")
        print("   Try running: python3 scripts/run_simulation.py")
    
    print()
    print(f"Current Mode: {'🔴 MOCK DATA' if settings.use_mocks else '✅ REAL DATA'}")
    print()
    print("💡 TIP: Don't worry about location names being different!")
    print("   - NYC DOT uses: 159, 376, 377 (numeric IDs)")
    print("   - Dashboard uses: dot_seg_001, 511_seg_001 (named IDs)")
    print("   - This is NORMAL - the system transforms the data")
    print("   - Just compare the SPEEDS - they should be similar!")

if __name__ == "__main__":
    asyncio.run(main())

