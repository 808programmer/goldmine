from django.apps import AppConfig
import os
from pathlib import Path


class MiningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mining'

    def ready(self):
        """Register signals when the app is ready"""
        import mining.signals
        # Create extracted_texts directory if it doesn't exist
        extracted_texts_dir = Path('media/extracted_texts')
        extracted_texts_dir.mkdir(parents=True, exist_ok=True)
