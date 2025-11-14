#!/usr/bin/env python3
"""
Professional Data Verification Script
Checks data flow at each stage: API → Raw DB → Processed DB → Dashboard
"""
import asyncio
import sys
import os
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.config import settings

class DataVerificationResult:
    """Structured verification result"""
    def __init__(self):
        self.stage1_api_available = False
        self.stage1_api_data_count = 0
        self.stage1_api_sample = []
        
        self.stage2_raw_db_available = False
        self.stage2_raw_db_count = 0
        self.stage2_raw_db_fresh = False
        self.stage2_raw_db_last_ingestion = None
        self.stage2_raw_db_sample = []
        
        self.stage3_processed_available = False
        self.stage3_processed_count = 0
        self.stage3_processed_fresh = False
        self.stage3_processed_last_update = None
        self.stage3_processed_sample = []
        
        self.stage4_dashboard_available = False
        self.stage4_dashboard_count = 0
        self.stage4_dashboard_sample = []
        
        self.issues = []
        self.warnings = []
        self.recommendations = []

async def verify_stage1_api() -> Dict:
    """Stage 1: Verify API is accessible and returns data"""
    result = {
        "available": False,
        "data_count": 0,
        "sample": [],
        "error": None
    }
    
    try:
        url = settings.nyc_dot_traffic_speeds_url
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params={"$limit": 10, "$order": "data_as_of DESC"}
            )
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, list):
                result["available"] = True
                result["data_count"] = len(data)
                result["sample"] = data[:3]  # First 3 records
            else:
                result["error"] = "API returned empty or invalid response"
                
    except Exception as e:
        result["error"] = str(e)
    
    return result

async def verify_stage2_raw_db() -> Dict:
    """Stage 2: Verify raw data is stored in MongoDB"""
    result = {
        "available": False,
        "count": 0,
        "fresh": False,
        "last_ingestion": None,
        "sample": [],
        "error": None
    }
    
    try:
        db = get_database()
        
        # Check raw_traffic_dot collection
        raw_docs = await db.raw_traffic_dot.find({}).sort("timestamp", -1).limit(10).to_list(length=10)
        
        if raw_docs:
            result["available"] = True
            result["count"] = await db.raw_traffic_dot.count_documents({})
            
            # Get most recent timestamp
            if raw_docs[0].get("timestamp"):
                result["last_ingestion"] = raw_docs[0]["timestamp"]
                
                # Check if data is fresh (within last hour)
                if isinstance(result["last_ingestion"], datetime):
                    age = datetime.utcnow() - result["last_ingestion"]
                    result["fresh"] = age < timedelta(hours=1)
                else:
                    result["fresh"] = False
            
            # Sample records
            result["sample"] = []
            for doc in raw_docs[:3]:
                result["sample"].append({
                    "segment_id": doc.get("segment_id", "Unknown"),
                    "speed_mph": doc.get("speed_mph", 0),
                    "timestamp": doc.get("timestamp"),
                    "source": doc.get("source", "unknown")
                })
        else:
            result["error"] = "No raw data found in database"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

async def verify_stage3_processed() -> Dict:
    """Stage 3: Verify processed data exists"""
    result = {
        "available": False,
        "count": 0,
        "fresh": False,
        "last_update": None,
        "sample": [],
        "error": None
    }
    
    try:
        db = get_database()
        
        # Check segments_state collection
        processed_docs = await db.segments_state.find({}).sort("timestamp_bucket", -1).limit(10).to_list(length=10)
        
        if processed_docs:
            result["available"] = True
            result["count"] = await db.segments_state.count_documents({})
            
            # Get most recent timestamp
            if processed_docs[0].get("timestamp_bucket"):
                result["last_update"] = processed_docs[0]["timestamp_bucket"]
                
                # Check if data is fresh (within last hour)
                if isinstance(result["last_update"], datetime):
                    age = datetime.utcnow() - result["last_update"]
                    result["fresh"] = age < timedelta(hours=1)
                else:
                    result["fresh"] = False
            
            # Sample records
            result["sample"] = []
            for doc in processed_docs[:3]:
                result["sample"].append({
                    "segment_id": doc.get("segment_id", "Unknown"),
                    "speed_mph": doc.get("speed_mph", 0),
                    "congestion_index": doc.get("congestion_index", 0),
                    "timestamp_bucket": doc.get("timestamp_bucket"),
                    "sources": list(doc.get("sources", []))
                })
        else:
            result["error"] = "No processed data found in database"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

async def verify_stage4_dashboard() -> Dict:
    """Stage 4: Verify dashboard can access data"""
    result = {
        "available": False,
        "count": 0,
        "sample": [],
        "error": None
    }
    
    try:
        db = get_database()
        
        # Check segments_state (what dashboard uses)
        dashboard_docs = await db.segments_state.find({}).sort("timestamp_bucket", -1).limit(5).to_list(length=5)
        
        if dashboard_docs:
            result["available"] = True
            result["count"] = len(dashboard_docs)
            
            # Sample records
            result["sample"] = []
            for doc in dashboard_docs[:3]:
                result["sample"].append({
                    "segment_id": doc.get("segment_id", "Unknown"),
                    "speed_mph": doc.get("speed_mph", 0),
                    "congestion_index": doc.get("congestion_index", 0),
                    "timestamp_bucket": str(doc.get("timestamp_bucket", "N/A"))[:19]
                })
        else:
            result["error"] = "No data available for dashboard"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def compare_speeds(api_data: List, raw_db_data: List) -> Dict:
    """Compare speeds between API and raw DB"""
    comparison = {
        "match": False,
        "api_speeds": [],
        "db_speeds": [],
        "difference": None,
        "message": ""
    }
    
    # Extract speeds from API
    for item in api_data[:5]:
        speed = item.get("speed", item.get("speed_mph", 0))
        if isinstance(speed, (int, float)) and speed > 0:
            comparison["api_speeds"].append(float(speed))
    
    # Extract speeds from DB
    for item in raw_db_data[:5]:
        speed = item.get("speed_mph", 0)
        if isinstance(speed, (int, float)) and speed > 0:
            comparison["db_speeds"].append(float(speed))
    
    if comparison["api_speeds"] and comparison["db_speeds"]:
        avg_api = sum(comparison["api_speeds"]) / len(comparison["api_speeds"])
        avg_db = sum(comparison["db_speeds"]) / len(comparison["db_speeds"])
        comparison["difference"] = abs(avg_api - avg_db)
        
        if comparison["difference"] < 15:
            comparison["match"] = True
            comparison["message"] = f"✅ Speeds match (difference: {comparison['difference']:.1f} mph)"
        else:
            comparison["message"] = f"⚠️  Speeds differ (difference: {comparison['difference']:.1f} mph) - may be different time periods"
    elif comparison["api_speeds"]:
        comparison["message"] = "⚠️  API has data but DB doesn't - ingestion may not have run"
    elif comparison["db_speeds"]:
        comparison["message"] = "⚠️  DB has data but API doesn't - may be using mock data"
    else:
        comparison["message"] = "❌ No speed data to compare"
    
    return comparison

async def main():
    print("=" * 80)
    print("🔍 PROFESSIONAL DATA VERIFICATION")
    print("=" * 80)
    print()
    print("Verifying data flow at each stage:")
    print("  Stage 1: API → Raw DB")
    print("  Stage 2: Raw DB → Processed DB")
    print("  Stage 3: Processed DB → Dashboard")
    print()
    
    await connect_to_mongo()
    
    # Stage 1: API Verification
    print("=" * 80)
    print("📡 STAGE 1: API Availability")
    print("=" * 80)
    stage1 = await verify_stage1_api()
    
    if stage1["available"]:
        print(f"✅ API is accessible")
        print(f"   Records available: {stage1['data_count']}")
        if stage1["sample"]:
            print(f"   Sample record: Speed={stage1['sample'][0].get('speed', 'N/A')} mph, ID={stage1['sample'][0].get('id', 'N/A')}")
    else:
        print(f"❌ API is not accessible")
        print(f"   Error: {stage1['error']}")
    
    print()
    
    # Stage 2: Raw DB Verification
    print("=" * 80)
    print("💾 STAGE 2: Raw Database Storage")
    print("=" * 80)
    stage2 = await verify_stage2_raw_db()
    
    if stage2["available"]:
        print(f"✅ Raw data is stored")
        print(f"   Total records: {stage2['count']}")
        
        if stage2["last_ingestion"]:
            if isinstance(stage2["last_ingestion"], datetime):
                age = datetime.utcnow() - stage2["last_ingestion"]
                age_str = f"{age.seconds // 60} minutes ago" if age.seconds < 3600 else f"{age.seconds // 3600} hours ago"
                print(f"   Last ingestion: {age_str}")
            else:
                print(f"   Last ingestion: {stage2['last_ingestion']}")
        
        if stage2["fresh"]:
            print(f"   ✅ Data is fresh (< 1 hour old)")
        else:
            print(f"   ⚠️  Data is stale (> 1 hour old)")
            print(f"      → Run ingestion: python3 scripts/run_simulation.py")
        
        if stage2["sample"]:
            print(f"   Sample: {stage2['sample'][0]['segment_id']} @ {stage2['sample'][0]['speed_mph']:.1f} mph")
    else:
        print(f"❌ No raw data in database")
        print(f"   Error: {stage2['error']}")
        print(f"   → Run ingestion: python3 scripts/run_simulation.py")
    
    print()
    
    # Compare API vs Raw DB
    if stage1["available"] and stage2["available"]:
        print("=" * 80)
        print("🔗 COMPARISON: API vs Raw DB")
        print("=" * 80)
        comparison = compare_speeds(stage1["sample"], stage2["sample"])
        print(comparison["message"])
        if comparison["api_speeds"] and comparison["db_speeds"]:
            print(f"   API average: {sum(comparison['api_speeds'])/len(comparison['api_speeds']):.1f} mph")
            print(f"   DB average: {sum(comparison['db_speeds'])/len(comparison['db_speeds']):.1f} mph")
        print()
    
    # Stage 3: Processed DB Verification
    print("=" * 80)
    print("⚙️  STAGE 3: Processed Database")
    print("=" * 80)
    stage3 = await verify_stage3_processed()
    
    if stage3["available"]:
        print(f"✅ Processed data exists")
        print(f"   Total records: {stage3['count']}")
        
        if stage3["last_update"]:
            if isinstance(stage3["last_update"], datetime):
                age = datetime.utcnow() - stage3["last_update"]
                age_str = f"{age.seconds // 60} minutes ago" if age.seconds < 3600 else f"{age.seconds // 3600} hours ago"
                print(f"   Last update: {age_str}")
            else:
                print(f"   Last update: {stage3['last_update']}")
        
        if stage3["fresh"]:
            print(f"   ✅ Data is fresh (< 1 hour old)")
        else:
            print(f"   ⚠️  Data is stale (> 1 hour old)")
            print(f"      → Run cleaning: python3 scripts/run_simulation.py")
        
        if stage3["sample"]:
            seg = stage3["sample"][0]
            print(f"   Sample: {seg['segment_id']} @ {seg['speed_mph']:.1f} mph, {seg['congestion_index']*100:.0f}% congestion")
    else:
        print(f"❌ No processed data in database")
        print(f"   Error: {stage3['error']}")
        print(f"   → Run cleaning: python3 scripts/run_simulation.py")
    
    print()
    
    # Stage 4: Dashboard Verification
    print("=" * 80)
    print("🖥️  STAGE 4: Dashboard Data")
    print("=" * 80)
    stage4 = await verify_stage4_dashboard()
    
    if stage4["available"]:
        print(f"✅ Dashboard can access data")
        print(f"   Records available: {stage4['count']}")
        if stage4["sample"]:
            seg = stage4["sample"][0]
            print(f"   Sample: {seg['segment_id']} @ {seg['speed_mph']:.1f} mph, {seg['congestion_index']*100:.0f}% congestion")
            print(f"   Timestamp: {seg['timestamp_bucket']}")
    else:
        print(f"❌ Dashboard has no data")
        print(f"   Error: {stage4['error']}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 80)
    print()
    
    issues = []
    warnings = []
    
    if not stage1["available"]:
        issues.append("❌ API is not accessible")
    elif stage1["data_count"] == 0:
        warnings.append("⚠️  API returned no data")
    
    if not stage2["available"]:
        issues.append("❌ No raw data stored - ingestion not run")
    elif not stage2["fresh"]:
        warnings.append("⚠️  Raw data is stale - run ingestion")
    
    if not stage3["available"]:
        issues.append("❌ No processed data - cleaning not run")
    elif not stage3["fresh"]:
        warnings.append("⚠️  Processed data is stale - run cleaning")
    
    if not stage4["available"]:
        issues.append("❌ Dashboard has no data")
    
    # Check USE_MOCKS setting
    if settings.use_mocks:
        warnings.append("⚠️  USE_MOCKS=true - using fake data")
    else:
        print("✅ USE_MOCKS=false - using real data")
    
    if issues:
        print("🚨 ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not issues and not warnings:
        print("✅ ALL CHECKS PASSED!")
        print("   Your data pipeline is working correctly!")
    else:
        print("💡 RECOMMENDATIONS:")
        if not stage2["available"] or not stage2["fresh"]:
            print("   1. Run ingestion: python3 scripts/run_simulation.py")
        if not stage3["available"] or not stage3["fresh"]:
            print("   2. Run cleaning: python3 scripts/run_simulation.py")
        if settings.use_mocks:
            print("   3. Set USE_MOCKS=false in .env for real data")
    
    print()
    print(f"Current Mode: {'🔴 MOCK DATA' if settings.use_mocks else '✅ REAL DATA'}")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())

