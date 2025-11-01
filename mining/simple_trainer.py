"""
SIMPLE GOLD PREDICTION MODEL TRAINER
=====================================

This is a simplified, single-file trainer that:
1. Reads text files from extracted_texts/
2. Uses GPT-5 to extract gold indicators and coordinates
3. Trains a simple classifier: "Contains gold deposit info" (1) or "Doesn't" (0)
4. Saves the model

No complex orchestration, no multi-agent systems, just straightforward training.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from django.utils import timezone as django_timezone

# Django imports
from django.conf import settings

# ML imports
try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    import joblib
except ImportError:
    print("⚠️  Warning: ML packages not installed. Install: pandas, numpy, scikit-learn, joblib")

# OpenAI import
try:
    from openai import OpenAI
except ImportError:
    print("⚠️  Warning: OpenAI package not installed. Run: pip install openai")

logger = logging.getLogger(__name__)


class SimpleGoldTrainer:
    """
    Simple, no-nonsense gold prediction model trainer.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.extracted_texts_dir = Path(settings.MEDIA_ROOT) / 'extracted_texts'
        self.model_dir = Path(settings.BASE_DIR) / 'mining' / 'models'
        self.model_dir.mkdir(exist_ok=True)
        
    def train(self) -> Dict[str, Any]:
        """
        Main training function - does everything in order.
        
        Returns:
            Dict with success status, results, and any errors
        """
        try:
            print("\n" + "="*60)
            print("🚀 STARTING SIMPLE GOLD PREDICTION TRAINING")
            print("="*60)
            
            # Step 1: Load text files
            print("\n📂 Step 1: Loading text files...")
            text_files = self._load_text_files()
            if not text_files:
                return {
                    'success': False,
                    'error': 'No text files found',
                    'recommendation': 'Upload PDFs and run OCR extraction first'
                }
            print(f"   ✅ Loaded {len(text_files)} text files")
            
            # Step 2: Extract features with GPT-5
            print("\n🤖 Step 2: Extracting features with GPT-5...")
            features_list = []
            for i, text_data in enumerate(text_files, 1):
                print(f"   Processing {i}/{len(text_files)}: {text_data['filename'][:50]}...")
                features = self._extract_features_simple(text_data['text'])
                if features:
                    features['filename'] = text_data['filename']
                    features_list.append(features)
                    print(f"      → Found {features['coordinate_count']} coords, {features['indicator_count']} indicators")
            
            if not features_list:
                return {
                    'success': False,
                    'error': 'GPT-5 could not extract any features',
                    'recommendation': 'Check OpenAI API key and text quality'
                }
            print(f"   ✅ Extracted features from {len(features_list)} documents")
            
            # Step 3: Create training dataset
            print("\n📊 Step 3: Creating training dataset...")
            df = self._create_simple_dataset(features_list)
            self._last_df = df  # Store for metadata
            print(f"   ✅ Created dataset with {len(df)} samples")
            print(f"      Features: {list(df.columns)}")
            
            # Step 4: Train model
            print("\n🎯 Step 4: Training Random Forest classifier...")
            model_results = self._train_simple_model(df)
            if not model_results['success']:
                return model_results
            print(f"   ✅ Model trained!")
            print(f"      Accuracy: {model_results['accuracy']:.1%}")
            
            # Step 5: Save model
            print("\n💾 Step 5: Saving model...")
            self._save_model(model_results['model'], model_results['scaler'], df, model_results['accuracy'])
            print(f"   ✅ Model saved to {self.model_dir}")
            
            print("\n" + "="*60)
            print("✅ TRAINING COMPLETE!")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'documents_processed': len(text_files),
                'features_extracted': len(features_list),
                'samples_created': len(df),
                'accuracy': model_results['accuracy'],
                'model_path': str(self.model_dir),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def _load_text_files(self) -> List[Dict[str, str]]:
        """Load all text files from extracted_texts directory."""
        text_files = []
        
        if not self.extracted_texts_dir.exists():
            logger.error(f"Directory not found: {self.extracted_texts_dir}")
            return []
        
        for txt_file in self.extracted_texts_dir.glob('*.txt'):
            try:
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Only include files with substantial content
                if len(content) > 100:  # At least 100 characters
                    text_files.append({
                        'filename': txt_file.name,
                        'text': content[:10000]  # First 10k chars to save API costs
                    })
            except Exception as e:
                logger.warning(f"Could not read {txt_file}: {e}")
        
        return text_files
    
    def _extract_features_simple(self, text: str) -> Dict[str, Any]:
        """
        Use GPT-5 to extract simple features from geological text.
        
        Returns:
            Dict with coordinate_count, indicator_count, has_gold_info
        """
        if not self.client:
            logger.warning("OpenAI client not initialized, using fallback")
            return self._fallback_extraction(text)
        
        try:
            # Simple, focused prompt
            prompt = f"""Analyze this geological report excerpt and extract:

1. How many coordinate pairs (latitude/longitude) are mentioned? (exact or inferred from location names)
2. How many gold-related indicators are present? (gold, mineralization, veins, ore, etc.)
3. Does this text contain information about gold deposits? (yes/no)

Text:
{text[:5000]}

Respond in JSON format:
{{
    "coordinate_count": <number>,
    "gold_indicator_count": <number>,
    "has_gold_deposit_info": <true/false>,
    "confidence": <0-100>
}}"""

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a geological expert analyzing historical mining reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(result_text)
            
            return {
                'coordinate_count': result.get('coordinate_count', 0),
                'indicator_count': result.get('gold_indicator_count', 0),
                'has_gold_info': result.get('has_gold_deposit_info', False),
                'confidence': result.get('confidence', 50)
            }
            
        except Exception as e:
            logger.warning(f"GPT-5 extraction failed: {e}, using fallback")
            return self._fallback_extraction(text)
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Simple keyword-based extraction as fallback."""
        import re
        
        text_lower = text.lower()
        
        # Count coordinates (rough patterns)
        coord_patterns = [
            r'\d+\.\d+\s*[NS].*?\d+\.\d+\s*[EW]',  # 5.2N 58.5W
            r'lat.*?\d+\.\d+',  # latitude: 5.2
            r'lon.*?\d+\.\d+',  # longitude: -58.5
        ]
        coord_count = sum(len(re.findall(pattern, text_lower)) for pattern in coord_patterns)
        
        # Count gold indicators
        gold_keywords = [
            'gold', 'auriferous', 'mineralization', 'ore', 'deposit', 
            'vein', 'lode', 'nugget', 'placer', 'alluvial', 'mine', 'mining'
        ]
        indicator_count = sum(text_lower.count(keyword) for keyword in gold_keywords)
        
        has_gold_info = indicator_count >= 3 or coord_count >= 1
        
        return {
            'coordinate_count': coord_count,
            'indicator_count': indicator_count,
            'has_gold_info': has_gold_info,
            'confidence': 60
        }
    
    def _create_simple_dataset(self, features_list: List[Dict]) -> pd.DataFrame:
        """
        Create a simple training dataset from extracted features.
        
        Target: has_gold_info (1 = yes, 0 = no)
        Features: coordinate_count, indicator_count, confidence
        """
        data = []
        for features in features_list:
            data.append({
                'coordinate_count': features['coordinate_count'],
                'indicator_count': features['indicator_count'],
                'confidence': features['confidence'],
                'has_gold_info': 1 if features['has_gold_info'] else 0
            })
        
        df = pd.DataFrame(data)
        
        # Count how many of each class we have
        positive_count = df['has_gold_info'].sum()
        negative_count = len(df) - positive_count
        
        # Add synthetic samples to ensure at least 5 of each class
        MIN_SAMPLES_PER_CLASS = 5
        
        # Add synthetic negatives if needed
        if negative_count < MIN_SAMPLES_PER_CLASS:
            needed = MIN_SAMPLES_PER_CLASS - negative_count
            print(f"   ⚠️  Only {negative_count} negative samples, adding {needed} synthetic negatives...")
            negatives = []
            for _ in range(needed):
                negatives.append({
                    'coordinate_count': np.random.randint(0, 2),
                    'indicator_count': np.random.randint(0, 3),
                    'confidence': np.random.randint(20, 50),
                    'has_gold_info': 0
                })
            df = pd.concat([df, pd.DataFrame(negatives)], ignore_index=True)
        
        # Add synthetic positives if needed (rare, but possible)
        if positive_count < MIN_SAMPLES_PER_CLASS:
            needed = MIN_SAMPLES_PER_CLASS - positive_count
            print(f"   ⚠️  Only {positive_count} positive samples, adding {needed} synthetic positives...")
            positives = []
            for _ in range(needed):
                positives.append({
                    'coordinate_count': np.random.randint(3, 8),
                    'indicator_count': np.random.randint(5, 15),
                    'confidence': np.random.randint(60, 90),
                    'has_gold_info': 1
                })
            df = pd.concat([df, pd.DataFrame(positives)], ignore_index=True)
        
        # Shuffle the dataset
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        return df
    
    def _train_simple_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train a simple Random Forest classifier."""
        try:
            # Separate features and target
            X = df[['coordinate_count', 'indicator_count', 'confidence']]
            y = df['has_gold_info']
            
            # Check if we have enough samples
            if len(df) < 10:
                return {
                    'success': False,
                    'error': f'Not enough samples: {len(df)} (need at least 10, but only have {len(df)})'
                }
            
            # Check if we have both classes
            if y.nunique() < 2:
                return {
                    'success': False,
                    'error': 'Only one class present in data (need both gold/no-gold samples)'
                }
            
            # Check class distribution
            class_counts = y.value_counts()
            min_class_count = class_counts.min()
            print(f"   📊 Class distribution: {dict(class_counts)}")
            
            if min_class_count < 2:
                return {
                    'success': False,
                    'error': f'Least populated class has only {min_class_count} sample(s). Need at least 2 per class.'
                }
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Split data with stratification if possible
            try:
                # Try stratified split first
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y, test_size=0.2, random_state=42, stratify=y
                )
            except ValueError as e:
                # If stratified split fails, use regular split
                print(f"   ⚠️  Stratified split failed ({str(e)}), using regular split...")
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y, test_size=0.2, random_state=42
                )
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            
            # Evaluate
            accuracy = model.score(X_test, y_test)
            
            return {
                'success': True,
                'model': model,
                'scaler': scaler,
                'accuracy': accuracy
            }
            
        except Exception as e:
            logger.error(f"Model training failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_model(self, model, scaler, df=None, accuracy=None):
        """Save the trained model and scaler."""
        model_path = self.model_dir / 'simple_gold_model.joblib'
        scaler_path = self.model_dir / 'simple_gold_scaler.joblib'
        
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        
        # Save metadata (use Django's timezone-aware datetime)
        metadata = {
            'trained_at': django_timezone.now().isoformat(),
            'model_type': 'RandomForestClassifier',
            'features': ['coordinate_count', 'indicator_count', 'confidence'],
            'target': 'has_gold_info',
            'training_samples': len(df) if df is not None else None,
            'accuracy': float(accuracy) if accuracy is not None else None
        }
        metadata_path = self.model_dir / 'simple_gold_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)


def run_simple_training():
    """
    Convenience function to run training.
    Can be called from views or management commands.
    """
    trainer = SimpleGoldTrainer()
    return trainer.train()


if __name__ == '__main__':
    # Allow running as standalone script
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldMineAI.settings')
    django.setup()
    
    result = run_simple_training()
    print(f"\n📊 Result: {json.dumps(result, indent=2)}")

