"""
Training Status Service
Provides real-time status updates for training and uploads
"""
import logging
from typing import Dict, Optional
from django.utils import timezone
from django.core.cache import cache
from .models import PDFTextData, ModelVersion

logger = logging.getLogger(__name__)


class TrainingStatusService:
    """Service for tracking and reporting training status"""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def _safe_get_document_count(metrics: Dict) -> int:
        """Safely extract document_count from metrics, handling both dict and int types"""
        try:
            if not isinstance(metrics, dict):
                return 0
            
            document_count_data = metrics.get('document_count', {})
            
            if isinstance(document_count_data, dict):
                return int(document_count_data.get('count', 0))
            elif isinstance(document_count_data, (int, float)):
                return int(document_count_data)
            else:
                return 0
        except (ValueError, TypeError, AttributeError):
            return 0
    
    @staticmethod
    def get_upload_status() -> Dict:
        """Get current status of document uploads"""
        try:
            total = PDFTextData.objects.count()
            processed = PDFTextData.objects.filter(status='processed').count()
            processing = PDFTextData.objects.filter(status='processing').count()
            failed = PDFTextData.objects.filter(status='failed').count()
            pending = PDFTextData.objects.filter(status__in=['uploaded', 'unprocessed']).count()
            
            last_upload_obj = PDFTextData.objects.order_by('-created_at').first()
            
            return {
                'total': total,
                'processed': processed,
                'processing': processing,
                'failed': failed,
                'pending': pending,
                'success_rate': round((processed / total * 100) if total > 0 else 0, 2),
                'last_upload': last_upload_obj.created_at.isoformat() if last_upload_obj else None
            }
        except Exception as e:
            logger.error(f"Error getting upload status: {e}", exc_info=True)
            return {
                'total': 0,
                'processed': 0,
                'processing': 0,
                'failed': 0,
                'pending': 0,
                'success_rate': 0,
                'last_upload': None
            }
    
    @staticmethod
    def get_training_status() -> Dict:
        """Get current status of model training"""
        try:
            latest_version = ModelVersion.objects.order_by('-trained_at').first()
            
            if not latest_version:
                return {
                    'trained': False,
                    'has_model': False,
                    'message': 'No trained model found'
                }
            
            return {
                'trained': True,
                'has_model': latest_version.model_file_exists(),
                'latest_version': latest_version.version_number,
                'latest_trained_at': latest_version.trained_at.isoformat(),
                'accuracy': latest_version.accuracy,
                'f1_score': latest_version.f1_score,
                'data_quality_score': latest_version.data_quality_score,
                'documents_used': latest_version.documents_used,
                'is_active': latest_version.is_active,
                'deployment_status': latest_version.deployment_status,
                'model_file_exists': latest_version.model_file_exists()
            }
        except Exception as e:
            # Handle case where ModelVersion table doesn't exist yet
            logger.warning(f"ModelVersion table may not exist: {e}")
            return {
                'trained': False,
                'has_model': False,
                'message': 'Model versioning not initialized. Please run migrations.'
            }
    
    @staticmethod
    def get_validation_status() -> Dict:
        """Get current validation status"""
        try:
            from .training_data_validator import TrainingDataValidator
            
            validator = TrainingDataValidator()
            validation = validator.validate_all_requirements()
            
            return {
                'ready_for_training': validation['ready_for_training'],
                'quality_score': validation['metrics'].get('overall_quality_score', 0),
                'document_count': TrainingStatusService._safe_get_document_count(validation.get('metrics', {})),
                'errors': validation.get('errors', []),
                'warnings': validation.get('warnings', []),
                'recommendations': validation.get('recommendations', [])
            }
        except Exception as e:
            logger.error(f"Error getting validation status: {e}", exc_info=True)
            return {
                'ready_for_training': False,
                'quality_score': 0,
                'document_count': 0,
                'errors': [f'Validation error: {str(e)}'],
                'warnings': [],
                'recommendations': []
            }
    
    @staticmethod
    def get_auto_training_status() -> Dict:
        """Get status of automated training"""
        try:
            from .automated_training_service import AutomatedTrainingService
            
            service = AutomatedTrainingService()
            should_train = service.should_auto_train()
            
            return {
                'enabled': service.AUTO_TRAIN_ENABLED,
                'should_train': should_train.get('should_train', False),
                'reason': should_train.get('reason', 'Not checked'),
                'conditions_met': should_train.get('new_documents', 0) >= service.MIN_NEW_DOCUMENTS
            }
        except Exception as e:
            logger.error(f"Error getting auto-training status: {e}", exc_info=True)
            return {
                'enabled': False,
                'should_train': False,
                'reason': f'Error: {str(e)}',
                'conditions_met': False
            }
    
    @staticmethod
    def get_comprehensive_status() -> Dict:
        """Get comprehensive status of entire system"""
        upload_status = TrainingStatusService.get_upload_status()
        training_status = TrainingStatusService.get_training_status()
        validation_status = TrainingStatusService.get_validation_status()
        auto_training_status = TrainingStatusService.get_auto_training_status()
        
        return {
            'timestamp': timezone.now().isoformat(),
            'upload_status': upload_status,
            'training_status': training_status,
            'validation_status': validation_status,
            'auto_training_status': auto_training_status,
            'system_ready': True
        }
    
    @staticmethod
    def update_training_progress(stage: str, progress: float, message: str = ""):
        """Update training progress (can be used for progress bars)"""
        cache_key = 'training_progress'
        cache.set(
            cache_key,
            {
                'stage': stage,
                'progress': progress,
                'message': message,
                'timestamp': timezone.now().isoformat()
            },
            TrainingStatusService.CACHE_TIMEOUT
        )
        logger.info(f"Training progress: {stage} - {progress}% - {message}")
    
    @staticmethod
    def get_training_progress() -> Optional[Dict]:
        """Get current training progress"""
        return cache.get('training_progress')

