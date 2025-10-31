from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from django.db import transaction
from .models import PDFTextData

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PDFTextData)
def auto_train_on_new_documents(sender, instance, created, **kwargs):
    """
    Automatically trigger model retraining when new documents are processed
    
    This signal:
    1. Validates data quality
    2. Checks if conditions are met for auto-training
    3. Triggers automated training if conditions are met
    """
    # Only trigger for successfully processed documents
    if not (instance.status == 'processed' and instance.extracted_text):
        return
    
    # Import here to avoid circular imports
    try:
        from .automated_training_service import AutomatedTrainingService
        
        # Use transaction.on_commit to avoid race conditions
        def trigger_training():
            try:
                training_service = AutomatedTrainingService()
                
                # Check if we should auto-train
                should_train = training_service.should_auto_train()
                
                if should_train['should_train']:
                    logger.info(
                        f"📊 Auto-training triggered: {should_train['reason']}. "
                        f"Document: {instance.filename}"
                    )
                    
                    # Run training in background (async if possible)
                    result = training_service.trigger_auto_training(force=False)
                    
                    if result['success']:
                        logger.info(
                            f"✅ Auto-training completed: "
                            f"Version {result.get('version_number')} created"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Auto-training skipped: {result.get('message', result.get('reason'))}"
                        )
                else:
                    logger.debug(
                        f"⏸️ Auto-training not triggered: {should_train['reason']}"
                    )
                    
            except Exception as e:
                logger.error(f"Error in auto-training signal: {e}", exc_info=True)
        
        # Schedule training after transaction commits
        transaction.on_commit(trigger_training)
        
    except ImportError as e:
        logger.debug(f"Automated training service not available: {e}")
    except Exception as e:
        logger.error(f"Error setting up auto-training signal: {e}", exc_info=True) 