"""
Automated Training Service
Handles automated model retraining when new data is available
"""
import logging
from typing import Dict, Optional
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .training_data_validator import TrainingDataValidator
from .model_versioning import ModelVersionManager, ModelVersion
from .llm_model_trainer import LLMModelTrainer
from .model_trainer import train_model_from_dataset
from .models import PDFTextData, Dataset

logger = logging.getLogger(__name__)


class AutomatedTrainingService:
    """
    Service for automated model retraining
    """
    
    # Configuration
    MIN_NEW_DOCUMENTS = 3  # Minimum new documents before auto-retrain
    MIN_HOURS_SINCE_LAST_TRAIN = 24  # Minimum hours between auto-trains
    AUTO_TRAIN_ENABLED = True  # Can be disabled via settings
    
    def __init__(self):
        self.validator = TrainingDataValidator()
        self.version_manager = ModelVersionManager()
        self.llm_trainer = LLMModelTrainer()
    
    def should_auto_train(self) -> Dict:
        """
        Check if conditions are met for automatic training
        
        Returns:
            Dict with should_train (bool) and reason
        """
        if not self.AUTO_TRAIN_ENABLED:
            return {
                'should_train': False,
                'reason': 'Auto-training is disabled'
            }
        
        # Check for new processed documents
        latest_version = self.version_manager.get_latest_version()
        if latest_version:
            new_docs = PDFTextData.objects.filter(
                status='processed',
                created_at__gt=latest_version.trained_at
            ).count()
            
            hours_since_train = (
                timezone.now() - latest_version.trained_at
            ).total_seconds() / 3600
            
            if new_docs >= self.MIN_NEW_DOCUMENTS:
                return {
                    'should_train': True,
                    'reason': f'{new_docs} new documents available',
                    'new_documents': new_docs,
                    'hours_since_train': hours_since_train
                }
            
            if hours_since_train >= self.MIN_HOURS_SINCE_LAST_TRAIN:
                return {
                    'should_train': True,
                    'reason': f'{hours_since_train:.1f} hours since last training',
                    'new_documents': new_docs,
                    'hours_since_train': hours_since_train
                }
        else:
            # No previous training, check if we have minimum data
            validation = self.validator.validate_all_requirements()
            
            # Ensure validation is a dict
            if not isinstance(validation, dict):
                logger.warning(f"Validation result is not a dict: {type(validation)}")
                return {
                    'should_train': False,
                    'reason': 'Validation check failed - invalid result type'
                }
            
            if validation.get('ready_for_training', False):
                return {
                    'should_train': True,
                    'reason': 'First model training - data is ready',
                    'validation': validation
                }
        
        return {
            'should_train': False,
            'reason': 'Conditions not met for auto-training'
        }
    
    def trigger_auto_training(self, force: bool = False) -> Dict:
        """
        Trigger automated training if conditions are met
        
        Args:
            force: Force training even if conditions not met
            
        Returns:
            Dict with training results
        """
        try:
            # Validate requirements
            validation = self.validator.validate_all_requirements()
            
            # Ensure validation is a dict
            if not isinstance(validation, dict):
                logger.error(f"Validation result is not a dict: {type(validation)}")
                return {
                    'success': False,
                    'error': 'Validation check returned invalid result type',
                    'message': 'Training data validation failed'
                }
            
            if not force and not validation.get('ready_for_training', False):
                return {
                    'success': False,
                    'error': 'Data validation failed',
                    'validation': validation,
                    'message': 'Training data does not meet minimum requirements'
                }
            
            # Check if we should train (unless forced)
            if not force:
                should_train_check = self.should_auto_train()
                
                # Ensure should_train_check is a dict
                if not isinstance(should_train_check, dict):
                    logger.error(f"should_train_check is not a dict: {type(should_train_check)}")
                    return {
                        'success': False,
                        'error': 'Training check returned invalid result type',
                        'message': 'Unable to determine if training should proceed'
                    }
                
                if not should_train_check.get('should_train', False):
                    return {
                        'success': False,
                        'error': 'Training conditions not met',
                        'reason': should_train_check.get('reason', 'Unknown reason'),
                        'message': 'Not enough new data or too soon since last training'
                    }
            
            logger.info("🚀 Starting automated model training...")
            
            # Run training
            training_result = self._run_training(validation)
            
            # Ensure training_result is a dict
            if not isinstance(training_result, dict):
                logger.error(f"Training result is not a dict: {type(training_result)}, value: {training_result}")
                return {
                    'success': False,
                    'error': f'Training returned unexpected type: {type(training_result).__name__}',
                    'message': 'An error occurred during training execution'
                }
            
            if training_result.get('success', False):
                logger.info("✅ Automated training completed successfully")
            else:
                error_msg = training_result.get('error', 'Unknown error') if isinstance(training_result, dict) else 'Unknown error'
                logger.error(f"❌ Automated training failed: {error_msg}")
            
            return training_result
            
        except Exception as e:
            logger.error(f"Error in automated training: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'An error occurred during automated training'
            }
    
    def _run_training(self, validation: Dict) -> Dict:
        """
        Execute the training process
        
        Args:
            validation: Validation results
            
        Returns:
            Training results
        """
        try:
            # Use LLM trainer to process data and train model
            logger.info("Processing data with LLM trainer...")
            
            # Check if llm_result is a dict, if not convert or handle accordingly
            llm_result = self.llm_trainer.analyze_and_train_from_texts(limit=None)
            
            logger.info(f"LLM result type: {type(llm_result)}")
            logger.info(f"LLM result: {llm_result}")
            
            # Ensure llm_result is a dictionary
            if not isinstance(llm_result, dict):
                logger.error(f"Unexpected return type from LLM trainer: {type(llm_result)}")
                return {
                    'success': False,
                    'error': f'LLM trainer returned unexpected type: {type(llm_result).__name__}',
                    'stage': 'llm_processing'
                }
            
            if 'error' in llm_result or not llm_result.get('success', True):
                error_msg = llm_result.get('error', 'Unknown error in LLM processing')
                logger.error(f"LLM training failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'stage': 'llm_processing'
                }
            
            # Extract training results from nested structure
            training_results = llm_result.get('training_results', {})
            if not isinstance(training_results, dict):
                logger.warning(f"training_results is not a dict: {type(training_results)}, value: {training_results}")
                training_results = {}
            
            logger.info(f"Training results: {training_results}")
            
            # Extract training metrics - handle both direct and nested structures
            # Get accuracy from various possible locations
            accuracy = (
                training_results.get('test_accuracy') if isinstance(training_results, dict) else None
            ) or llm_result.get('model_accuracy') or llm_result.get('accuracy') or 0
            
            # Get f1_score from various possible locations
            f1_score = (
                training_results.get('test_f1') if isinstance(training_results, dict) else None
            ) or llm_result.get('f1_score') or 0
            
            training_metrics = {
                'accuracy': float(accuracy) if accuracy else 0,
                'f1_score': float(f1_score) if f1_score else 0,
                'training_samples': int(llm_result.get('training_samples', 0)),
                'validation_samples': int(training_results.get('validation_samples', 0)) if isinstance(training_results, dict) else 0,
                'documents_used': int(llm_result.get('texts_processed', 0)),
                'coordinates_generated': int(llm_result.get('features_extracted', 0)),
                'model_type': str(training_results.get('model_type', 'RandomForest')) if isinstance(training_results, dict) else 'RandomForest',
                'hyperparameters': training_results.get('hyperparameters') if isinstance(training_results, dict) else None,
            }
            
            logger.info(f"Training metrics extracted: {training_metrics}")
            
            # Get data quality score from validation - handle different structures
            data_quality_score = 0
            try:
                if isinstance(validation, dict) and 'metrics' in validation:
                    metrics = validation['metrics']
                    if isinstance(metrics, dict):
                        data_quality_score = float(metrics.get('overall_quality_score', 0))
                    elif isinstance(metrics, (int, float)):
                        data_quality_score = float(metrics)
                elif isinstance(validation, dict) and 'overall_quality_score' in validation:
                    data_quality_score = float(validation.get('overall_quality_score', 0))
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Error extracting data_quality_score: {e}")
                data_quality_score = 0
            
            logger.info(f"Data quality score: {data_quality_score}")
            
            # Create model version
            latest_dataset = Dataset.objects.order_by('-uploaded_at').first()
            
            # Ensure training_metrics is a dict before accessing
            if not isinstance(training_metrics, dict):
                logger.error(f"training_metrics is not a dict: {type(training_metrics)}, value: {training_metrics}")
                training_metrics = {
                    'accuracy': 0,
                    'f1_score': 0,
                    'training_samples': 0,
                    'validation_samples': 0,
                    'documents_used': 0,
                    'coordinates_generated': 0,
                    'model_type': 'RandomForest',
                    'hyperparameters': None
                }
            
            documents_used = training_metrics.get('documents_used', 0) if isinstance(training_metrics, dict) else 0
            description = (
                f"Automated training with {documents_used} documents. "
                f"Data quality score: {data_quality_score:.2f}"
            )
            
            # Note: Model is already saved by LLM trainer, so we need to load it
            # For now, we'll create a version record referencing the default model path
            model_path = 'mining/models/mineral_prediction_model.joblib'
            
            # Generate version number
            version_number = self.version_manager._generate_version_number()
            
            # Create version record
            with transaction.atomic():
                # Deactivate previous active version
                ModelVersion.objects.filter(is_active=True).update(is_active=False)
                
                # Ensure all values are safe for database
                accuracy_val = training_metrics.get('accuracy') if isinstance(training_metrics, dict) else None
                f1_score_val = training_metrics.get('f1_score') if isinstance(training_metrics, dict) else None
                
                # Create new version
                model_version = ModelVersion.objects.create(
                    version_number=version_number,
                    model_path=model_path,
                    trained_at=timezone.now(),
                    trained_by='automated_system',
                    accuracy=float(accuracy_val) if accuracy_val is not None else None,
                    f1_score=float(f1_score_val) if f1_score_val is not None else None,
                    training_samples=int(training_metrics.get('training_samples', 0)) if isinstance(training_metrics, dict) else 0,
                    validation_samples=int(training_metrics.get('validation_samples', 0)) if isinstance(training_metrics, dict) else 0,
                    data_quality_score=float(data_quality_score),
                    documents_used=int(training_metrics.get('documents_used', 0)) if isinstance(training_metrics, dict) else 0,
                    coordinates_generated=int(training_metrics.get('coordinates_generated', 0)) if isinstance(training_metrics, dict) else 0,
                    model_type=str(training_metrics.get('model_type', 'RandomForest')) if isinstance(training_metrics, dict) else 'RandomForest',
                    hyperparameters=training_metrics.get('hyperparameters') if isinstance(training_metrics, dict) else None,
                    training_config={
                        'auto_trained': True,
                        'validation_passed': True
                    },
                    description=description,
                    is_active=True,
                    deployment_status='validated'
                )
            
            logger.info(f"✅ Created model version {version_number}")
            
            return {
                'success': True,
                'version_number': version_number,
                'model_version_id': model_version.id,
                'training_metrics': training_metrics,
                'data_quality_score': data_quality_score,
                'validation': validation,
                'message': f'Model training completed successfully. Version {version_number} created.'
            }
            
        except Exception as e:
            logger.error(f"Error during training execution: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stage': 'training_execution'
            }

