from django.core.management.base import BaseCommand
from mining.models import PDFTextData
from mining.services.pdf_service import PDFService
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Extract text from existing PDFs in the database - just OCR processing'

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
            '--status',
            type=str,
            choices=['uploaded', 'processing', 'failed', 'unprocessed'],
            help='Only process PDFs with specific status',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        force = options.get('force')
        dry_run = options.get('dry_run')
        status_filter = options.get('status')
        
        self.stdout.write('📖 Text Extraction from Existing PDFs (OCR Only)')
        self.stdout.write('=' * 50)
        
        # Get PDFs to process
        if force:
            pdfs = PDFTextData.objects.all()
            self.stdout.write('🔄 Force mode: Will reprocess ALL PDFs')
        else:
            if status_filter:
                pdfs = PDFTextData.objects.filter(status=status_filter)
                self.stdout.write(f'📊 Filtering by status: {status_filter}')
            else:
                pdfs = PDFTextData.objects.filter(is_processed=False)
                self.stdout.write('📊 Processing only unprocessed PDFs')
        
        if limit:
            pdfs = pdfs[:limit]
            self.stdout.write(f'📊 Limited to {limit} PDFs')
        
        self.stdout.write(f'📄 PDFs to process: {pdfs.count()}')
        
        if not pdfs.exists():
            self.stdout.write('❌ No PDFs found to process')
            return
        
        # Show PDFs that will be processed
        for pdf in pdfs:
            status_icon = {
                'uploaded': '📤',
                'processing': '🔄',
                'failed': '❌',
                'unprocessed': '⏳',
                'processed': '✅'
            }.get(pdf.status, '❓')
            
            self.stdout.write(f'   {status_icon} {pdf.filename} (Status: {pdf.status})')
            if pdf.extracted_text:
                self.stdout.write(f'     Text length: {len(pdf.extracted_text)} characters')
            else:
                self.stdout.write(f'     No extracted text')
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN: Would process the above PDFs')
            return
        
        # Initialize PDF service
        pdf_service = PDFService()
        
        # Process PDFs
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for pdf in pdfs:
            try:
                self.stdout.write(f'\n🔄 Processing: {pdf.filename}')
                
                # Skip if already processed and not forcing
                if pdf.is_processed and not force:
                    self.stdout.write('   ⏭️  Already processed, skipping...')
                    continue
                
                # Extract text with OCR (if needed)
                if not pdf.extracted_text or len(pdf.extracted_text.strip()) == 0:
                    self.stdout.write('   📖 Extracting text with OCR...')
                    
                    if pdf.file_path:
                        # Get absolute file path
                        from django.conf import settings
                        absolute_file_path = os.path.join(settings.MEDIA_ROOT, pdf.file_path)
                        
                        if os.path.exists(absolute_file_path):
                            try:
                                # Extract text using Adobe OCR
                                extracted_text = pdf_service.ocr_service.extract_text_from_pdf(absolute_file_path)
                                
                                if extracted_text and len(extracted_text.strip()) > 0:
                                    pdf.extracted_text = extracted_text
                                    pdf.status = 'processed'
                                    pdf.is_processed = True
                                    pdf.save()
                                    self.stdout.write(f'   ✅ Extracted {len(extracted_text)} characters')
                                    success_count += 1
                                else:
                                    self.stdout.write('   ❌ No text extracted from PDF')
                                    pdf.status = 'failed'
                                    pdf.save()
                                    error_count += 1
                                    continue
                            except Exception as e:
                                self.stdout.write(f'   ❌ OCR failed: {str(e)}')
                                pdf.status = 'failed'
                                pdf.last_processing_error = str(e)
                                pdf.save()
                                error_count += 1
                                continue
                        else:
                            self.stdout.write(f'   ❌ PDF file not found: {absolute_file_path}')
                            pdf.status = 'failed'
                            pdf.save()
                            error_count += 1
                            continue
                    else:
                        self.stdout.write('   ❌ No file path found for PDF')
                        pdf.status = 'failed'
                        pdf.save()
                        error_count += 1
                        continue
                else:
                    self.stdout.write('   ✅ Text already extracted')
                    if not pdf.is_processed:
                        pdf.is_processed = True
                        pdf.save()
                        success_count += 1
                
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(f'❌ Error processing {pdf.filename}: {str(e)}')
                error_count += 1
                processed_count += 1
        
        # Summary
        self.stdout.write(f'\n📊 Text Extraction Summary')
        self.stdout.write('=' * 30)
        self.stdout.write(f'Total processed: {processed_count}')
        self.stdout.write(f'Successful: {success_count}')
        self.stdout.write(f'Failed: {error_count}')
        
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS('✅ Successfully extracted text from PDFs!'))
            self.stdout.write('📝 The extracted text is now available in the database.')
        else:
            self.stdout.write(self.style.ERROR('❌ No PDFs were successfully processed'))
