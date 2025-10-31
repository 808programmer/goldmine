"""
Model Versioning System
Tracks model versions, training history, and enables rollback
"""
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from django.utils import timezone
from django.conf import settings
from .models import ModelVersion
import joblib

logger = logging.getLogger(__name__)


class ModelVersionManager:
    """Manager class for model versioning operations"""
    
    def __init__(self):
        self.model_dir = Path('mining/models')
        self.model_dir.mkdir(exist_ok=True)
    
    def create_version(
        self,
        model,
        training_metrics: Dict,
        data_quality_score: float,
        training_config: Optional[Dict] = None,
        description: str = ""
    ) -> ModelVersion:
        """
        Create a new model version
        
        Args:
            model: Trained model object
            training_metrics: Dict with accuracy, f1_score, etc.
            data_quality_score: Overall data quality score
            training_config: Training configuration used
            description: Optional description
            
        Returns:
            ModelVersion instance
        """
        # Generate version number
        version_number = self._generate_version_number()
        
        # Save model to file
        model_filename = f"mineral_prediction_model_v{version_number.replace('.', '_')}.joblib"
        model_path = self.model_dir / model_filename
        
        joblib.dump(model, model_path)
        logger.info(f"Saved model to: {model_path}")
        
        # Create model version record
        model_version = ModelVersion.objects.create(
            version_number=version_number,
            model_path=str(model_path.relative_to(settings.BASE_DIR)),
            trained_at=timezone.now(),
            accuracy=training_metrics.get('accuracy'),
            f1_score=training_metrics.get('f1_score'),
            training_samples=training_metrics.get('training_samples', 0),
            validation_samples=training_metrics.get('validation_samples', 0),
            data_quality_score=data_quality_score,
            documents_used=training_metrics.get('documents_used', 0),
            coordinates_generated=training_metrics.get('coordinates_generated', 0),
            model_type=training_metrics.get('model_type', 'RandomForest'),
            hyperparameters=training_metrics.get('hyperparameters'),
            training_config=training_config or {},
            description=description,
            deployment_status='validated'
        )
        
        logger.info(f"Created model version {version_number}")
        return model_version
    
    def _generate_version_number(self) -> str:
        """Generate a unique version number"""
        # Format: YYYY.MM.DD.HHMM or increment if multiple today
        now = timezone.now()
        base_version = now.strftime('%Y.%m.%d')
        
        # Check how many versions exist today
        today_versions = ModelVersion.objects.filter(
            version_number__startswith=base_version
        ).count()
        
        if today_versions == 0:
            # Use timestamp for uniqueness
            version = f"{base_version}.{now.strftime('%H%M')}"
        else:
            # Increment version
            version = f"{base_version}.{today_versions + 1}"
        
        return version
    
    def get_active_version(self) -> Optional[ModelVersion]:
        """Get the currently active model version"""
        return ModelVersion.objects.filter(is_active=True).first()
    
    def get_latest_version(self) -> Optional[ModelVersion]:
        """Get the latest trained version"""
        return ModelVersion.objects.order_by('-trained_at').first()
    
    def list_versions(self, limit: int = 10) -> List[ModelVersion]:
        """List recent model versions"""
        return list(ModelVersion.objects.all()[:limit])
    
    def rollback_to_version(self, version_number: str) -> bool:
        """
        Rollback to a specific model version
        
        Args:
            version_number: Version to rollback to
            
        Returns:
            True if successful
        """
        try:
            target_version = ModelVersion.objects.get(version_number=version_number)
            
            if not target_version.model_file_exists():
                logger.error(f"Model file not found for version {version_number}")
                return False
            
            # Deactivate current version
            ModelVersion.objects.filter(is_active=True).update(is_active=False)
            
            # Activate target version
            target_version.activate()
            
            logger.info(f"Rolled back to model version {version_number}")
            return True
            
        except ModelVersion.DoesNotExist:
            logger.error(f"Model version {version_number} not found")
            return False
    
    def compare_versions(self, version1: str, version2: str) -> Dict:
        """Compare two model versions"""
        v1 = ModelVersion.objects.get(version_number=version1)
        v2 = ModelVersion.objects.get(version_number=version2)
        
        return {
            'version1': {
                'number': v1.version_number,
                'accuracy': v1.accuracy,
                'f1_score': v1.f1_score,
                'data_quality_score': v1.data_quality_score,
                'trained_at': v1.trained_at
            },
            'version2': {
                'number': v2.version_number,
                'accuracy': v2.accuracy,
                'f1_score': v2.f1_score,
                'data_quality_score': v2.data_quality_score,
                'trained_at': v2.trained_at
            },
            'improvements': {
                'accuracy_delta': (v2.accuracy or 0) - (v1.accuracy or 0),
                'f1_delta': (v2.f1_score or 0) - (v1.f1_score or 0),
                'quality_delta': (v2.data_quality_score or 0) - (v1.data_quality_score or 0)
            }
        }

