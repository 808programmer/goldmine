#!/usr/bin/env python3
"""
Batch Model Training Script
Simple command-line script to train models from extracted texts
"""

import os
import sys
import django
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldMineAI.settings')
django.setup()

from mining.llm_model_trainer import LLMModelTrainer
from mining.model_trainer import train_model_from_dataset
from mining.models import Dataset, TrainingRecord
from django.conf import settings

def train_model(limit=None, force=False, verbose=False):
    """
    Train the model from extracted texts
    
    Args:
        limit: Maximum number of text files to process
        force: Force retraining
        verbose: Enable verbose output
    """
    try:
        print("🚀 Starting model training...")
        
        # Initialize trainer
        llm_trainer = LLMModelTrainer()
        
        # Process texts with LLM
        print("📚 Processing text files...")
        llm_results = llm_trainer.analyze_and_train_from_texts(
            limit=limit, 
            reprocess=force
        )
        
        if not llm_results.get('success'):
            print(f"❌ LLM processing failed: {llm_results.get('error')}")
            return False
        
        print("✅ LLM processing completed")
        
        # Find or create dataset
        dataset = Dataset.objects.filter(processed=True).order_by('-uploaded_at').first()
        if not dataset:
            print("❌ No processed dataset found")
            return False
        
        # Train the model
        print("🤖 Training ML model...")
        training_results = train_model_from_dataset(dataset)
        
        if not training_results.get('success'):
            print(f"❌ Model training failed: {training_results.get('error')}")
            return False
        
        # Create training record
        training_record = TrainingRecord.objects.create(
            dataset=dataset,
            accuracy=training_results['test_accuracy'],
            model_path=training_results['model_path']
        )
        
        print("🎉 Training completed successfully!")
        print(f"   Accuracy: {training_results['test_accuracy']:.4f}")
        print(f"   F1 Score: {training_results.get('test_f1', 'N/A')}")
        print(f"   Model Type: {training_results.get('model_type', 'Unknown')}")
        print(f"   Training Record ID: {training_record.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False

def check_status():
    """Check current training status"""
    try:
        extracted_texts_path = Path(settings.MEDIA_ROOT) / 'extracted_texts'
        text_files = list(extracted_texts_path.glob('*.txt')) if extracted_texts_path.exists() else []
        
        datasets = Dataset.objects.filter(processed=True).count()
        recent_trainings = TrainingRecord.objects.all().order_by('-training_date')[:3]
        
        print("📊 Current Status:")
        print(f"   Extracted texts: {len(text_files)}")
        print(f"   Available datasets: {datasets}")
        print(f"   Recent trainings: {len(recent_trainings)}")
        
        if recent_trainings:
            print("\n📈 Recent Training Results:")
            for tr in recent_trainings:
                print(f"   • {tr.dataset.name if tr.dataset else 'Unknown'}: {tr.accuracy:.4f} ({tr.training_date.strftime('%Y-%m-%d %H:%M')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Train GoldMine AI model from extracted texts')
    parser.add_argument('--limit', type=int, help='Maximum number of text files to process')
    parser.add_argument('--force', action='store_true', help='Force retraining')
    parser.add_argument('--status', action='store_true', help='Check status only')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.status:
        check_status()
        return
    
    success = train_model(
        limit=args.limit,
        force=args.force,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
