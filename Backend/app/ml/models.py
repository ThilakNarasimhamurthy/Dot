"""
ML models for congestion prediction
Uses scikit-learn for local, fast, accurate predictions
"""
import os
import logging
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from app.config import settings
from app.ml.features import FeatureEngineer

logger = logging.getLogger(__name__)


class CongestionPredictor:
    """ML model for predicting traffic congestion"""
    
    def __init__(self, segment_id: Optional[str] = None):
        """
        Initialize predictor
        
        Args:
            segment_id: Optional segment ID for segment-specific model
        """
        self.segment_id = segment_id
        self.model = None
        self.feature_engineer = FeatureEngineer()
        self.model_type = settings.ml_model_type
        self.model_path = settings.ml_model_path
        self.is_trained = False
        
        # Create model directory if it doesn't exist
        os.makedirs(self.model_path, exist_ok=True)
    
    def _create_model(self) -> object:
        """Create model instance based on config"""
        if self.model_type == "gradient_boosting":
            return GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                verbose=0
            )
        elif self.model_type == "random_forest":
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
                verbose=0
            )
        else:
            # Default to gradient boosting
            logger.warning(f"Unknown model type {self.model_type}, using gradient_boosting")
            return GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """
        Train the model
        
        Args:
            X: Feature matrix
            y: Target values (speeds or congestion indices)
        
        Returns:
            Dictionary with training metrics
        """
        if len(X) == 0 or len(y) == 0:
            raise ValueError("Training data is empty")
        
        # Create and train model
        self.model = self._create_model()
        self.model.fit(X, y)
        self.is_trained = True
        
        # Calculate metrics
        y_pred = self.model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        r2 = r2_score(y, y_pred)
        
        metrics = {
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2),
            "n_samples": len(X),
            "model_type": self.model_type
        }
        
        logger.info(f"Model trained: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.3f}")
        
        return metrics
    
    def predict(self, features: Dict) -> Tuple[float, float]:
        """
        Predict speed and congestion for given features
        
        Args:
            features: Feature dictionary
        
        Returns:
            Tuple of (predicted_speed, predicted_congestion_index)
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first or load a saved model.")
        
        # Convert features to array
        feature_names = self.feature_engineer.get_feature_names()
        feature_vector = np.array([features.get(name, 0) for name in feature_names]).reshape(1, -1)
        
        # Predict speed (we'll train separate models or use one model for speed)
        # For simplicity, we'll predict speed and derive congestion
        predicted_speed = self.model.predict(feature_vector)[0]
        
        # Clamp speed to reasonable values
        predicted_speed = max(5.0, min(50.0, predicted_speed))
        
        # Calculate congestion from speed (inverse relationship)
        max_speed = 50.0
        predicted_congestion = max(0.0, min(1.0, 1.0 - (predicted_speed / max_speed)))
        
        return predicted_speed, predicted_congestion
    
    def save_model(self, filename: Optional[str] = None):
        """Save trained model to disk"""
        if not self.is_trained or self.model is None:
            raise ValueError("No trained model to save")
        
        if filename is None:
            model_name = f"{self.model_type}_{self.segment_id or 'global'}.joblib"
            filename = os.path.join(self.model_path, model_name)
        
        joblib.dump(self.model, filename)
        logger.info(f"Model saved to {filename}")
    
    def load_model(self, filename: Optional[str] = None):
        """Load trained model from disk"""
        if filename is None:
            model_name = f"{self.model_type}_{self.segment_id or 'global'}.joblib"
            filename = os.path.join(self.model_path, model_name)
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Model file not found: {filename}")
        
        self.model = joblib.load(filename)
        self.is_trained = True
        logger.info(f"Model loaded from {filename}")


class ModelTrainer:
    """Trainer for congestion prediction models"""
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.db = None  # Will be set from database module
    
    async def prepare_training_data(
        self,
        segment_id: Optional[str] = None,
        days_back: int = 7
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from MongoDB
        
        Args:
            segment_id: Optional segment ID (None = all segments)
            days_back: Number of days of history to use
        
        Returns:
            Tuple of (X, y) where X is features and y is target speeds
        """
        from app.database import get_database
        self.db = get_database()
        
        # Get historical data
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        
        query = {
            "timestamp_bucket": {"$gte": cutoff_time}
        }
        if segment_id:
            query["segment_id"] = segment_id
        
        # Fetch data
        cursor = self.db.segments_state.find(query).sort("timestamp_bucket", 1)
        history_docs = await cursor.to_list(length=10000)
        
        # Lower minimum for demo - normally 50, but allow 8 for demo purposes
        min_records = 8 if settings.environment == "development" else 50
        if len(history_docs) < min_records:
            raise ValueError(f"Insufficient training data: {len(history_docs)} records (minimum: {min_records})")
        
        # Group by segment and time bucket
        segments_data = {}
        for doc in history_docs:
            seg_id = doc.get("segment_id")
            if seg_id not in segments_data:
                segments_data[seg_id] = []
            segments_data[seg_id].append(doc)
        
        # Create features and targets
        X_list = []
        y_list = []
        
        for seg_id, seg_history in segments_data.items():
            # Sort by timestamp (oldest first for lookback)
            seg_history.sort(key=lambda x: x.get("timestamp_bucket", datetime.min))
            
            # Create sliding window features
            for i in range(len(seg_history) - 1):
                # Use history up to current point
                history_window = seg_history[:i+1]
                # Reverse to get newest first (as expected by feature engineer)
                history_window = list(reversed(history_window))
                
                # Get features for current time
                current_time = history_window[0].get("timestamp_bucket")
                features = self.feature_engineer.create_features(history_window, current_time)
                
                if features:
                    # Target is the NEXT period's speed
                    target_speed = seg_history[i+1].get("speed_mph", 0)
                    
                    if target_speed > 0:  # Valid speed
                        # Convert features to array
                        feature_names = self.feature_engineer.get_feature_names()
                        feature_vector = [features.get(name, 0) for name in feature_names]
                        
                        X_list.append(feature_vector)
                        y_list.append(target_speed)
        
        if len(X_list) == 0:
            raise ValueError("No valid training samples created")
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        logger.info(f"Prepared training data: {len(X)} samples, {X.shape[1]} features")
        
        return X, y
    
    async def train_global_model(self) -> Dict:
        """Train a global model for all segments"""
        logger.info("Training global congestion prediction model...")
        
        X, y = await self.prepare_training_data(segment_id=None, days_back=settings.ml_training_history_days)
        
        predictor = CongestionPredictor(segment_id=None)
        metrics = predictor.train(X, y)
        predictor.save_model()
        
        return metrics
    
    async def train_segment_model(self, segment_id: str) -> Dict:
        """Train a segment-specific model"""
        logger.info(f"Training model for segment {segment_id}...")
        
        X, y = await self.prepare_training_data(segment_id=segment_id, days_back=settings.ml_training_history_days)
        
        predictor = CongestionPredictor(segment_id=segment_id)
        metrics = predictor.train(X, y)
        predictor.save_model()
        
        return metrics

