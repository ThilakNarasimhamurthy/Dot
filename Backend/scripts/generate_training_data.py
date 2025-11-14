#!/usr/bin/env python3
"""
Generate synthetic historical data for ML training
Creates realistic time-series data with proper sequences
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.config import settings

async def generate_training_data():
    """Generate synthetic historical segments_state data with time sequences"""
    await connect_to_mongo()
    db = get_database()
    
    # Generate data for last 7 days
    segments = ["511_seg_001", "511_seg_002", "511_seg_003", "dot_seg_001", "dot_seg_002", "dot_seg_003"]
    
    records_created = 0
    now = datetime.utcnow()
    
    print("Generating historical training data...")
    print(f"Segments: {len(segments)}")
    print(f"Time period: Last 7 days")
    print(f"Interval: Every 15 minutes")
    print()
    
    # Generate data going backwards in time
    for day in range(7):  # 7 days of history
        for hour in range(24):  # 24 hours per day
            for minute in [0, 15, 30, 45]:  # Every 15 minutes
                # Calculate timestamp (going backwards from now)
                timestamp = now - timedelta(days=day, hours=23-hour, minutes=45-minute)
                timestamp_bucket = timestamp.replace(second=0, microsecond=0)
                
                for segment_id in segments:
                    # Simulate realistic traffic patterns
                    # Rush hours (7-9 AM, 5-7 PM) have lower speeds
                    hour_of_day = timestamp.hour
                    is_rush_hour = (hour_of_day >= 7 and hour_of_day < 9) or (hour_of_day >= 17 and hour_of_day < 19)
                    is_night = hour_of_day >= 22 or hour_of_day < 6
                    
                    if is_rush_hour:
                        base_speed = random.uniform(8, 20)  # Slow during rush hour
                        congestion = random.uniform(0.6, 0.9)  # High congestion
                    elif is_night:
                        base_speed = random.uniform(35, 50)  # Fast at night
                        congestion = random.uniform(0.1, 0.3)  # Low congestion
                    else:
                        base_speed = random.uniform(25, 40)  # Normal speed
                        congestion = random.uniform(0.3, 0.6)  # Moderate congestion
                    
                    # Add some randomness and smooth transitions
                    speed = base_speed + random.uniform(-5, 5)
                    speed = max(5, min(55, speed))  # Clamp between 5-55 mph
                    
                    # Add correlation between speed and congestion
                    congestion = max(0.0, min(1.0, congestion))
                    
                    segment_data = {
                        "segment_id": segment_id,
                        "timestamp_bucket": timestamp_bucket,
                        "speed_mph": round(speed, 1),
                        "congestion_index": round(congestion, 2),
                        "incident_flag": random.random() < 0.05,  # 5% chance of incident
                        "transit_delay_flag": random.random() < 0.1,  # 10% chance of transit delay
                        "pm25_nearby": round(random.uniform(10, 35), 1),
                        "data_confidence_score": round(random.uniform(0.85, 1.0), 2),
                        "latitude": 40.7128 + random.uniform(-0.1, 0.1),
                        "longitude": -74.0060 + random.uniform(-0.1, 0.1)
                    }
                    
                    # Use upsert to avoid duplicates
                    result = await db.segments_state.update_one(
                        {
                            "segment_id": segment_id,
                            "timestamp_bucket": timestamp_bucket
                        },
                        {"$set": segment_data},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        records_created += 1
                    
                    # Progress indicator
                    if records_created % 100 == 0:
                        print(f"  Generated {records_created} records...", end='\r')
    
    print(f"\n✓ Generated {records_created} historical records")
    print(f"✓ Data spans last 7 days")
    print(f"✓ Time intervals: Every 15 minutes")
    
    # Verify final count
    final_count = await db.segments_state.count_documents({})
    print(f"\n✓ Total segments_state records in database: {final_count}")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(generate_training_data())

