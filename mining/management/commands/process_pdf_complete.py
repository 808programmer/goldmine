from django.core.management.base import BaseCommand
from mining.models import PDFTextData
from mining.services.pdf_service import PDFService
from mining.llm_geological_analyzer import LLMGeologicalAnalyzer
from mining.llm_data_processor import LLMDataProcessor
from mining.llm_model_trainer import LLMModelTrainer
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Complete PDF processing workflow: OCR → OpenAI Analysis → Dataset Generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of PDFs to process',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if already processed',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing',
        )
        parser.add_argument(
            '--skip-ocr',
            action='store_true',
            help='Skip OCR processing (assume text already extracted)',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        force = options.get('force')
        dry_run = options.get('dry_run')
        skip_ocr = options.get('skip_ocr')
        
        self.stdout.write('🔄 Complete PDF Processing Workflow')
        self.stdout.write('=' * 50)
        
        # Get PDFs to process
        if force:
            pdfs = PDFTextData.objects.all()
        else:
            pdfs = PDFTextData.objects.filter(is_processed=False)
        
        if limit:
            pdfs = pdfs[:limit]
        
        self.stdout.write(f'📄 PDFs to process: {pdfs.count()}')
        
        if not pdfs.exists():
            self.stdout.write('❌ No PDFs found to process')
            return
        
        # Show PDFs that will be processed
        for pdf in pdfs:
            self.stdout.write(f'   - {pdf.filename} (ID: {pdf.id})')
            if pdf.extracted_text:
                self.stdout.write(f'     Text length: {len(pdf.extracted_text)} characters')
            else:
                self.stdout.write(f'     No extracted text')
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN: Would process the above PDFs')
            return
        
        # Process PDFs
        pdf_service = PDFService()
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for pdf in pdfs:
            try:
                self.stdout.write(f'\n🔄 Processing: {pdf.filename}')
                
                # Step 1: Extract text with Adobe OCR (if needed)
                if not skip_ocr and (not pdf.extracted_text or len(pdf.extracted_text.strip()) == 0):
                    self.stdout.write('   📖 Extracting text with Adobe OCR...')
                    
                    if pdf.file_path:
                        # Get absolute file path
                        from django.conf import settings
                        absolute_file_path = os.path.join(settings.MEDIA_ROOT, pdf.file_path)
                        
                        if os.path.exists(absolute_file_path):
                            # Extract text using Adobe OCR
                            extracted_text = pdf_service.ocr_service.extract_text_from_pdf(absolute_file_path)
                            
                            if extracted_text and len(extracted_text.strip()) > 0:
                                pdf.extracted_text = extracted_text
                                pdf.save()
                                self.stdout.write(f'   ✅ Extracted {len(extracted_text)} characters')
                            else:
                                self.stdout.write('   ❌ No text extracted from PDF')
                                error_count += 1
                                continue
                        else:
                            self.stdout.write(f'   ❌ PDF file not found: {absolute_file_path}')
                            error_count += 1
                            continue
                    else:
                        self.stdout.write('   ❌ No file path found for PDF')
                        error_count += 1
                        continue
                else:
                    self.stdout.write('   ✅ Text already extracted')
                
                # Step 2: Analyze with OpenAI
                if pdf.extracted_text and len(pdf.extracted_text.strip()) > 0:
                    self.stdout.write('   🤖 Analyzing with OpenAI API...')
                    
                    analyzer = LLMGeologicalAnalyzer()
                    features = analyzer.extract_geological_features(pdf.extracted_text)
                    
                    if features and features.get('coordinates'):
                        self.stdout.write(f'   ✅ Found {len(features["coordinates"])} coordinates')
                        
                        # Step 3: Create geological features
                        self.stdout.write('   🗺️  Creating geological features...')
                        trainer = LLMModelTrainer()
                        geological_features = trainer._create_geological_features(features, pdf)
                        
                        if geological_features:
                            self.stdout.write(f'   ✅ Created {len(geological_features)} geological features')
                            
                            # Step 4: Create training dataset
                            self.stdout.write('   📊 Creating training dataset...')
                            processor = LLMDataProcessor()
                            training_data = processor._convert_features_to_training_data(features, pdf)
                            
                            if training_data:
                                # Save dataset to CSV
                                import pandas as pd
                                import time
                                from django.core.files import File
                                from mining.models import Dataset
                                
                                # Create datasets directory
                                datasets_dir = os.path.join(settings.MEDIA_ROOT, 'datasets')
                                os.makedirs(datasets_dir, exist_ok=True)
                                
                                # Generate filename
                                timestamp = int(time.time())
                                dataset_filename = f"openai_training_data_{timestamp}.csv"
                                dataset_path = os.path.join(datasets_dir, dataset_filename)
                                
                                # Save dataset
                                df = pd.DataFrame(training_data)
                                df.to_csv(dataset_path, index=False)
                                
                                # Create Dataset record with correct file path
                                relative_path = os.path.join('datasets', dataset_filename)
                                dataset = Dataset.objects.create(
                                    name=f"OpenAI Analysis - {pdf.filename}",
                                    description=f"Dataset generated from OpenAI analysis of {pdf.filename}",
                                    file=relative_path,
                                    rows_count=len(df),
                                    processed=True
                                )
                                
                                # Update PDF record
                                pdf.dataset = dataset
                                pdf.is_processed = True
                                pdf.save()
                                
                                self.stdout.write(f'   ✅ Created dataset: {dataset_filename} ({len(df)} rows)')
                                success_count += 1
                            else:
                                self.stdout.write('   ❌ No training data created')
                                error_count += 1
                        else:
                            self.stdout.write('   ❌ No geological features created')
                            error_count += 1
                    else:
                        self.stdout.write('   ❌ No coordinates found in OpenAI analysis')
                        error_count += 1
                else:
                    self.stdout.write('   ❌ No text available for analysis')
                    error_count += 1
                
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(f'❌ Error processing {pdf.filename}: {str(e)}')
                error_count += 1
                processed_count += 1
        
        # Summary
        self.stdout.write(f'\n📊 Processing Summary')
        self.stdout.write('=' * 30)
        self.stdout.write(f'Total processed: {processed_count}')
        self.stdout.write(f'Successful: {success_count}')
        self.stdout.write(f'Failed: {error_count}')
        
        if success_count > 0:
            self.stdout.write('✅ Successfully processed PDFs with complete workflow!')
        else:
            self.stdout.write('❌ No PDFs were successfully processed') 