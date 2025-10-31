import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
import joblib
import os
from pathlib import Path
from django.conf import settings
from .models import GeologicalFeature, MineralDeposit, SoilAnalysis, PredictionHistory

class MineralPredictionModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.model_path = Path(settings.BASE_DIR) / 'mining' / 'models' / 'mineral_prediction_model.joblib'
        self.scaler_path = Path(settings.BASE_DIR) / 'mining' / 'models' / 'mineral_scaler.joblib'
        self.encoders_path = Path(settings.BASE_DIR) / 'mining' / 'models' / 'mineral_encoders.joblib'
        
        # Create models directory if it doesn't exist
        os.makedirs(Path(settings.BASE_DIR) / 'mining' / 'models', exist_ok=True)
        
        # Try to load existing model
        self.load_model()

    def prepare_features(self, features_df):
        """Prepare features for model training or prediction"""
        # Create copies to avoid modifying original data
        df = features_df.copy()
        
        # Remove target variable and other non-feature columns
        columns_to_remove = ['mineral_type', 'concentration', 'depth', 'extraction_difficulty']
        for col in columns_to_remove:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Handle categorical variables
        categorical_columns = ['soil_type', 'geological_formation', 'feature_type', 'elevation_band']
        for col in categorical_columns:
            if col in df.columns:
                # Always fit on all unique values in the full DataFrame
                unique_values = features_df[col].dropna().unique().tolist()
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    self.label_encoders[col].fit(unique_values)
                else:
                    # If new unique values are found, refit the encoder
                    current_classes = set(self.label_encoders[col].classes_)
                    all_classes = set(unique_values) | current_classes
                    if all_classes != current_classes:
                        self.label_encoders[col].fit(list(all_classes))
                df[col] = self.label_encoders[col].transform(df[col])
        
        # Scale numerical features
        numerical_columns = ['latitude', 'longitude', 'elevation', 'ph_level', 'organic_matter']
        # Only scale columns that exist in the dataframe
        existing_numerical = [col for col in numerical_columns if col in df.columns]
        if existing_numerical:
            numerical_features = df[existing_numerical].copy()
            
            if not hasattr(self.scaler, 'mean_'):
                self.scaler.fit(numerical_features)
            
            df[existing_numerical] = self.scaler.transform(numerical_features)
        
        return df

    def extract_training_data(self):
        """Extract training data from the database"""
        # Get all geological features with their related data
        features = GeologicalFeature.objects.all()
        
        data = []
        for feature in features:
            # Get related mineral deposits
            mineral_deposits = MineralDeposit.objects.filter(feature=feature)
            # Get related soil analysis
            soil_analyses = SoilAnalysis.objects.filter(feature=feature)
            
            # Calculate distance from center (approximate center of Guyana)
            center_lat, center_lng = 4.8, -58.5
            dist_from_center = ((feature.latitude - center_lat) ** 2 + (feature.longitude - center_lng) ** 2) ** 0.5
            # Determine elevation band
            if feature.elevation < 100:
                elevation_band = 'low'
            elif feature.elevation < 500:
                elevation_band = 'medium'
            else:
                elevation_band = 'high'
            
            for deposit in mineral_deposits:
                soil = soil_analyses.first()  # Get the first soil analysis if available
                data.append({
                    'latitude': feature.latitude,
                    'longitude': feature.longitude,
                    'elevation': feature.elevation,
                    'dist_from_center': dist_from_center,
                    'soil_type': soil.soil_type if soil else 'unknown',
                    'geological_formation': self._extract_geological_formation(feature.description) if hasattr(self, '_extract_geological_formation') else feature.description,
                    'elevation_band': elevation_band,
                    'ph_level': soil.ph_level if soil else 7.0,
                    'organic_matter': soil.organic_matter if soil else 0.0,
                    'mineral_type': deposit.mineral_type,
                    'concentration': deposit.concentration,
                    'depth': deposit.depth,
                    'extraction_difficulty': deposit.extraction_difficulty
                })
        return pd.DataFrame(data)

    def train(self):
        """Train the prediction model"""
        # Extract training data
        df = self.extract_training_data()
        
        if df.empty:
            raise ValueError("No training data available")
        
        # Prepare features
        X = self.prepare_features(df)
        y = df['mineral_type']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Initialize and train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        # Save model and related objects
        self.save_model()
        
        return {
            'accuracy': accuracy,
            'f1_score': f1,
            'classification_report': classification_report(y_test, y_pred)
        }

    def predict(self, features):
        """Make predictions for new data"""
        if self.model is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        # Prepare features
        X = self.prepare_features(pd.DataFrame([features]))
        
        # Make prediction
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        # Get confidence score
        confidence = np.max(probabilities)
        
        return {
            'mineral_type': prediction,
            'confidence': confidence,
            'probabilities': dict(zip(self.model.classes_, probabilities))
        }

    def save_model(self):
        """Save the model and related objects"""
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        joblib.dump(self.label_encoders, self.encoders_path)

    def load_model(self):
        """Load the model and related objects"""
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            self.label_encoders = joblib.load(self.encoders_path)
            return True
        except:
            return False

    def get_feature_importance(self):
        """Get feature importance from the model"""
        if self.model is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        feature_names = list(self.label_encoders.keys()) + ['latitude', 'longitude', 'elevation', 'ph_level', 'organic_matter']
        importance = self.model.feature_importances_
        
        return dict(zip(feature_names, importance)) 