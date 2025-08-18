from django.db import models
from django.contrib.auth.models import User
import uuid

class PDFUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('unprocessed', 'Unprocessed'),  # New status for failed OCR that can be retried
        ('retry_pending', 'Retry Pending'),  # Status when user requests retry
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    pdf_file = models.FileField(upload_to='uploads/pdfs/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    extracted_text = models.TextField(blank=True, null=True)
    ocr_job_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)
    file_hash = models.CharField(max_length=64, blank=True, null=True, help_text='MD5 hash of the file for duplicate detection')
    
    # Processing tracking fields
    processing_attempts = models.IntegerField(default=0)  # Number of processing attempts
    last_processing_error = models.TextField(blank=True, null=True)  # Last error message
    last_processing_attempt = models.DateTimeField(null=True, blank=True)  # Last processing attempt
    processing_method = models.CharField(max_length=50, blank=True, null=True)  # Method used (Adobe OCR, PyPDF2, etc.)
    document_type = models.CharField(max_length=50, default='geological_survey', choices=[
        ('geological_survey', 'Geological Survey'),
        ('mining_map', 'Mining Map'),
    ])
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.status}"
