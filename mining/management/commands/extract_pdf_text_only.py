from django.core.management.base import BaseCommand
from django.conf import settings
from mining.models import PDFTextData
from mining.services.pdf_service import PDFService
import os
import shutil
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Extract text from PDFs without full geological analysis - just OCR processing'

    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path',
            type=str,
            help='Path to folder containing PDFs to process'
        )
        parser.add_argument(
            '--document-type',
            type=str,
            default='geological_survey',
            choices=['geological_survey', 'mining_map'],
            help='Document type for all PDFs (default: geological_survey)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip PDFs that already exist in the database'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )
        parser.add_argument(
            '--force-reprocess',
            action='store_true',
            help='Force reprocessing of existing PDFs'
        )

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        document_type = options['document_type']
        skip_existing = options['skip_existing']
        dry_run = options['dry_run']
        force_reprocess = options['force_reprocess']

        self.stdout.write('📖 PDF Text Extraction Only (OCR Processing)')
        self.stdout.write('=' * 50)
        self.stdout.write(f'📁 Source folder: {folder_path}')
        self.stdout.write(f'📄 Document type: {document_type}')
        
        # Check if folder exists
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f'❌ Folder does not exist: {folder_path}'))
            return
        
        if not os.path.isdir(folder_path):
            self.stdout.write(self.style.ERROR(f'❌ Path is not a directory: {folder_path}'))
            return

        # Find all PDF files
        pdf_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith('.pdf'):
                pdf_files.append(file)
        
        if not pdf_files:
            self.stdout.write('❌ No PDF files found in the specified folder')
            return
        
        self.stdout.write(f'📄 Found {len(pdf_files)} PDF files:')
        for pdf_file in pdf_files:
            self.stdout.write(f'   - {pdf_file}')
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN: Would process the above PDFs')
            return
        
        # Initialize PDF service
        pdf_service = PDFService()
        
        # Process each PDF
        processed_count = 0
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for pdf_file in pdf_files:
            try:
                pdf_path = os.path.join(folder_path, pdf_file)
                self.stdout.write(f'\n🔄 Processing: {pdf_file}')
                
                # Check if PDF already exists
                existing_pdf = PDFTextData.objects.filter(
                    original_filename=pdf_file
                ).first()
                
                if existing_pdf and not force_reprocess:
                    if skip_existing:
                        self.stdout.write(f'   ⏭️  Skipping existing PDF: {pdf_file}')
                        skipped_count += 1
                        continue
                    else:
                        self.stdout.write(f'   ⚠️  PDF already exists: {pdf_file}')
                        if not force_reprocess:
                            self.stdout.write('   Use --force-reprocess to reprocess existing PDFs')
                            continue
                
                # Copy PDF to media folder
                media_pdf_path = f'uploads/pdfs/{pdf_file}'
                absolute_media_path = os.path.join(settings.MEDIA_ROOT, media_pdf_path)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(absolute_media_path), exist_ok=True)
                
                # Copy file
                shutil.copy2(pdf_path, absolute_media_path)
                self.stdout.write(f'   📁 Copied to: {media_pdf_path}')
                
                # Create or update PDFTextData record
                if existing_pdf and force_reprocess:
                    pdf_record = existing_pdf
                    pdf_record.file_path = media_pdf_path
                    pdf_record.status = 'uploaded'
                    pdf_record.is_processed = False
                    pdf_record.extracted_text = ''
                    pdf_record.processed_text = ''
                    pdf_record.save()
                    self.stdout.write(f'   🔄 Updated existing record (ID: {pdf_record.id})')
                else:
                    pdf_record = PDFTextData.objects.create(
                        filename=pdf_file,
                        original_filename=pdf_file,
                        file_path=media_pdf_path,
                        document_type=document_type,
                        status='uploaded'
                    )
                    self.stdout.write(f'   ✅ Created new record (ID: {pdf_record.id})')
                
                # Extract text with OCR
                self.stdout.write('   📖 Extracting text with OCR...')
                try:
                    extracted_text = pdf_service.ocr_service.extract_text_from_pdf(absolute_media_path)
                    if extracted_text and len(extracted_text.strip()) > 0:
                        pdf_record.extracted_text = extracted_text
                        pdf_record.status = 'processed'
                        pdf_record.is_processed = True
                        pdf_record.save()
                        self.stdout.write(f'   ✅ Extracted {len(extracted_text)} characters')
                        success_count += 1
                    else:
                        self.stdout.write('   ❌ No text extracted from PDF')
                        pdf_record.status = 'failed'
                        pdf_record.save()
                        error_count += 1
                        continue
                except Exception as e:
                    self.stdout.write(f'   ❌ OCR failed: {str(e)}')
                    pdf_record.status = 'failed'
                    pdf_record.last_processing_error = str(e)
                    pdf_record.save()
                    error_count += 1
                    continue
                
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(f'❌ Error processing {pdf_file}: {str(e)}')
                error_count += 1
                processed_count += 1
        
        # Summary
        self.stdout.write(f'\n📊 Text Extraction Summary')
        self.stdout.write('=' * 40)
        self.stdout.write(f'Total PDFs found: {len(pdf_files)}')
        self.stdout.write(f'Processed: {processed_count}')
        self.stdout.write(f'Successful: {success_count}')
        self.stdout.write(f'Failed: {error_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS('✅ Successfully extracted text from PDFs!'))
            self.stdout.write('📝 The extracted text is now available in the database for further processing.')
        else:
            self.stdout.write(self.style.ERROR('❌ No PDFs were successfully processed'))
