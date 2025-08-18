from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from .models import PDFTextData

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PDFTextData)
def auto_process_with_llm_on_pdf_text_creation(sender, instance, created, **kwargs):
    """
    Alternative: Automatically process with LLM when new PDF text is created
    This is disabled by default to avoid conflicts with the main training signal
    """
    # This signal is disabled by default - uncomment to enable
    return
    
    if created and not instance.is_processed:
        logger.info(f"New PDF text created: {instance.filename}. Triggering LLM processing...")
        
        try:
            # Import here to avoid circular imports
            from .llm_data_processor import LLMDataProcessor
            
            # Initialize processor
            processor = LLMDataProcessor()
            
            # Process and train model
            result = processor.process_and_train_model(limit=None)
            
            if 'error' not in result:
                logger.info(f"✅ LLM processing successful! "
                          f"Training data size: {result.get('training_data_size', 0)}")
            else:
                logger.error(f"❌ LLM processing failed: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error in LLM processing: {e}") 