"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Core
    mongodb_uri: str = "mongodb://localhost:27017"  # Override via MONGODB_URI env var in production
    mongodb_db_name: str = "smartcity_dashboard"
    environment: str = "development"  # development | production
    use_mocks: bool = True  # Set to False to use real APIs
    
    # CORS Configuration
    cors_origins: str = "http://localhost:8080,http://localhost:3000,http://localhost:5173,http://127.0.0.1:8080,http://127.0.0.1:3000"  # Comma-separated list, override via CORS_ORIGINS env var
    
    # Traffic - 511NY (Optional - we use NYC DOT OpenData instead)
    ny511_api_key: Optional[str] = None
    ny511_base_url: str = "https://api.511.org/traffic/v2"
    
    # Traffic - NYC DOT OpenData (No API key needed - Public datasets)
    nyc_dot_traffic_speeds_url: str = "https://data.cityofnewyork.us/resource/i4gi-tjb9.json"  # DOT Traffic Speeds NBE
    nyc_dot_traffic_volume_url: str = "https://data.cityofnewyork.us/resource/7ym2-wayt.json"  # Automated Traffic Volume Counts
    nyc_dot_collisions_url: str = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"  # Motor Vehicle Collisions
    nyc_dot_traffic_calming_url: str = "https://data.cityofnewyork.us/resource/hz4p-9f7s.json"  # Turn-Traffic-Calming
    
    # Transit - MTA
    mta_api_key: Optional[str] = None
    mta_gtfs_vehicle_url: str = "https://gtfsrt.prod.obanyc.com/vehiclePositions"
    mta_gtfs_tripupdates_url: str = "https://gtfsrt.prod.obanyc.com/tripUpdates"
    mta_gtfs_alerts_url: str = "https://gtfsrt.prod.obanyc.com/alerts"
    
    # Transit - NYC DOT OpenData (Bus breakdowns/delays)
    nyc_bus_breakdowns_url: str = "https://data.cityofnewyork.us/resource/ez4e-fazm.json"  # Bus Breakdown and Delays
    
    # Air Quality - NYC OpenData
    nyc_air_quality_url: str = "https://data.cityofnewyork.us/resource/q68s-8qxv.json"  # NYCCAS Air Pollution Rasters
    airnow_api_key: Optional[str] = None
    airnow_base_url: str = "https://www.airnowapi.org/aq/observation/zipCode/current"
    
    # Additional NYC OpenData
    nyc_311_requests_url: str = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"  # 311 Service Requests
    
    # Hugging Face (Optional - for explanation agent)
    huggingface_api_token: Optional[str] = None
    huggingface_model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"
    
    # Scheduling Intervals (seconds)
    ingestion_interval_traffic: int = 30
    ingestion_interval_transit: int = 60
    ingestion_interval_air_quality: int = 900  # 15 minutes
    
    # Prediction Configuration
    prediction_window_15min: bool = True
    prediction_window_30min: bool = True
    
    # ML Model Configuration
    ml_model_type: str = "gradient_boosting"  # gradient_boosting | random_forest | exponential_smoothing
    ml_model_path: str = "models/congestion_models"
    ml_training_history_days: int = 7  # Days of history to use for training
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    # Legacy aliases for backward compatibility
    @property
    def nyc_dot_traffic_url(self) -> str:
        """Legacy alias - use nyc_dot_traffic_speeds_url"""
        return self.nyc_dot_traffic_speeds_url
    
    @property
    def api_key_mta(self) -> Optional[str]:
        return self.mta_api_key
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Global settings instance
settings = Settings()

