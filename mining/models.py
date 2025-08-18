from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

# Create your models here.
class Miner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, default="Unknown Miner")
    license_number = models.CharField(max_length=100, unique=True, default="UNKNOWN")
    contact_info = models.TextField(default="")
    experience_years = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['created']),
        ]

    def __str__(self):
        return self.name

class Dataset(models.Model):
    """
    Model to track uploaded or generated datasets
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to='datasets/')
    rows_count = models.IntegerField(default=0)
    processed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['processed']),
        ]

    def __str__(self):
        return self.name

class GeologicalSurvey(models.Model):
    """
    Model to store geological survey information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)  # Region in Guyana
    survey_date = models.DateField()
    author = models.CharField(max_length=255)
    description = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['survey_id']),
            models.Index(fields=['survey_date']),
            models.Index(fields=['location']),
        ]
        ordering = ['-survey_date']

    def __str__(self):
        return self.title

class GeologicalFeature(models.Model):
    """
    Model to store geological features extracted from surveys
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(GeologicalSurvey, on_delete=models.CASCADE, related_name='features')
    feature_type = models.CharField(max_length=100)  # e.g., 'Mineral Deposit', 'Fault Line', 'Rock Formation'
    latitude = models.FloatField()
    longitude = models.FloatField()
    elevation = models.FloatField()
    description = models.TextField()
    confidence_score = models.FloatField(default=1.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    name = models.CharField(max_length=255, blank=True)
    gold_probability = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['feature_type']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['gold_probability']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.feature_type} at ({self.latitude}, {self.longitude})"

class MineralDeposit(models.Model):
    """
    Model to store specific mineral deposit information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.ForeignKey(GeologicalFeature, on_delete=models.CASCADE, related_name='mineral_deposits')
    mineral_type = models.CharField(max_length=100)
    concentration = models.FloatField(null=True, blank=True)  # Concentration if available
    depth = models.FloatField(null=True, blank=True)  # Depth of deposit
    estimated_quantity = models.FloatField(null=True, blank=True)  # Estimated quantity if available
    extraction_difficulty = models.CharField(max_length=20, default='Medium')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['mineral_type']),
            models.Index(fields=['concentration']),
            models.Index(fields=['extraction_difficulty']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.mineral_type} deposit in {self.feature}"

class SoilAnalysis(models.Model):
    """
    Model to store soil analysis data
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.ForeignKey(GeologicalFeature, on_delete=models.CASCADE, related_name='soil_analyses')
    soil_type = models.CharField(max_length=100)
    ph_level = models.FloatField(null=True, blank=True)
    organic_matter = models.FloatField(null=True, blank=True)  # Percentage
    mineral_content = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['soil_type']),
            models.Index(fields=['ph_level']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Soil analysis for {self.feature}"

class PDFTextData(models.Model):
    """
    Enhanced model to store extracted text from PDFs with geological survey context
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    extracted_text = models.TextField()
    processed_text = models.TextField(blank=True, default="")
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, null=True, blank=True)
    text_file_path = models.CharField(max_length=500, blank=True, default="")
    file_path = models.CharField(max_length=500, blank=True, default="")  # Path to the uploaded PDF file
    is_large_file = models.BooleanField(default=False)
    
    # Status field for tracking upload and processing status
    status = models.CharField(
        max_length=20, 
        choices=[
            ('uploaded', 'Uploaded'),
            ('processing', 'Processing'),
            ('processed', 'Processed'),
            ('failed', 'Failed'),
            ('unprocessed', 'Unprocessed'),  # New status for failed OCR that can be retried
            ('retry_pending', 'Retry Pending'),  # Status when user requests retry
        ],
        default='uploaded'
    )
    
    # Duplicate detection fields
    file_hash = models.CharField(max_length=64, blank=True, default="")  # SHA-256 hash of file content
    content_hash = models.CharField(max_length=64, blank=True, default="")  # SHA-256 hash of extracted text
    file_size = models.BigIntegerField(null=True, blank=True)  # File size in bytes
    original_filename = models.CharField(max_length=255, blank=True, default="")  # Original uploaded filename
    
    # Quality metrics field
    quality_metrics = models.JSONField(null=True, blank=True)  # Store text quality metrics
    needs_manual_review = models.BooleanField(default=False)  # Flag for manual review
    
    # Processing tracking fields
    processing_attempts = models.IntegerField(default=0)  # Number of processing attempts
    last_processing_error = models.TextField(blank=True, null=True)  # Last error message
    last_processing_attempt = models.DateTimeField(null=True, blank=True)  # Last processing attempt
    processing_method = models.CharField(max_length=50, blank=True, null=True)  # Method used (Adobe OCR, PyPDF2, etc.)
    
    # Document type field for processing method selection
    document_type = models.CharField(
        max_length=20, 
        choices=[
            ('geological_survey', 'Geological Survey'),
            ('mining_map', 'Mining Map')
        ],
        default='geological_survey'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['filename']),
            models.Index(fields=['status']),  # Index for status tracking
            models.Index(fields=['file_path']),  # Index for file path tracking
            models.Index(fields=['file_hash']),  # Index for duplicate detection
            models.Index(fields=['content_hash']),  # Index for content-based duplicate detection
            models.Index(fields=['original_filename']),  # Index for filename-based duplicate detection
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.filename
    
    def is_duplicate(self):
        """
        Check if this document is a duplicate based on various criteria
        """
        # Check by file hash
        if self.file_hash and PDFTextData.objects.filter(file_hash=self.file_hash).exclude(id=self.id).exists():
            return True
        
        # Check by content hash
        if self.content_hash and PDFTextData.objects.filter(content_hash=self.content_hash).exclude(id=self.id).exists():
            return True
        
        # Check by original filename (case-insensitive)
        if self.original_filename:
            existing = PDFTextData.objects.filter(
                original_filename__iexact=self.original_filename
            ).exclude(id=self.id).first()
            if existing:
                return True
        
        # Check by filename (case-insensitive)
        existing = PDFTextData.objects.filter(
            filename__iexact=self.filename
        ).exclude(id=self.id).first()
        if existing:
            return True
        
        return False
    
    def get_duplicate_info(self):
        """
        Get information about existing duplicates
        """
        duplicates = []
        
        # Check by file hash
        if self.file_hash:
            file_hash_duplicates = PDFTextData.objects.filter(file_hash=self.file_hash).exclude(id=self.id)
            if file_hash_duplicates.exists():
                duplicates.extend([{
                    'type': 'file_hash',
                    'document': dup,
                    'reason': 'Same file content'
                } for dup in file_hash_duplicates])
        
        # Check by content hash
        if self.content_hash:
            content_hash_duplicates = PDFTextData.objects.filter(content_hash=self.content_hash).exclude(id=self.id)
            if content_hash_duplicates.exists():
                duplicates.extend([{
                    'type': 'content_hash',
                    'document': dup,
                    'reason': 'Same extracted text content'
                } for dup in content_hash_duplicates])
        
        # Check by original filename
        if self.original_filename:
            filename_duplicates = PDFTextData.objects.filter(
                original_filename__iexact=self.original_filename
            ).exclude(id=self.id)
            if filename_duplicates.exists():
                duplicates.extend([{
                    'type': 'filename',
                    'document': dup,
                    'reason': 'Same original filename'
                } for dup in filename_duplicates])
        
        return duplicates

class PredictionHistory(models.Model):
    """
    Enhanced model to store prediction history with geological context
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    latitude = models.FloatField()
    longitude = models.FloatField()
    elevation = models.FloatField(default=0)
    soil_type = models.CharField(max_length=100)
    geological_formation = models.CharField(max_length=100)
    probability = models.FloatField()
    confidence = models.FloatField()
    mineral_type = models.CharField(max_length=50, default='gold')
    depth_range = models.CharField(max_length=50, blank=True, default="")
    extraction_difficulty = models.CharField(max_length=20, default='Medium')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['mineral_type']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['soil_type']),
            models.Index(fields=['geological_formation']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.mineral_type} prediction at ({self.latitude}, {self.longitude})"

class TrainingRecord(models.Model):
    """
    Model to track model training records
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, null=True, blank=True)
    accuracy = models.FloatField()
    model_path = models.CharField(max_length=255)
    training_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['training_date']),
            models.Index(fields=['accuracy']),
        ]
        ordering = ['-training_date']

    def __str__(self):
        return f"Training record {self.id} - Accuracy: {self.accuracy:.3f}"

class UploadedFile(models.Model):
    """Model to store uploaded files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='uploaded')
    
    class Meta:
        indexes = [
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename

class GeologicalReport(models.Model):
    """
    Model to store processed geological reports for LLM querying
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    filename = models.CharField(max_length=255)
    source_file = models.ForeignKey(PDFTextData, on_delete=models.CASCADE, related_name='reports')
    
    # Report metadata
    author = models.CharField(max_length=255, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    region = models.CharField(max_length=100, blank=True)
    document_type = models.CharField(max_length=50, default='geological_survey')
    
    # Content storage
    full_text = models.TextField()  # Complete extracted text
    summary = models.TextField(blank=True)  # AI-generated summary
    key_findings = models.JSONField(default=dict)  # Structured key findings
    
    # Processing metadata
    processed_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(max_length=20, default='processed')
    confidence_score = models.FloatField(default=0.0)
    
    # Search and query optimization
    search_vector = models.TextField(blank=True)  # For full-text search
    tags = models.JSONField(default=list)  # Keywords and tags
    
    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['location']),
            models.Index(fields=['region']),
            models.Index(fields=['document_type']),
            models.Index(fields=['processed_at']),
            models.Index(fields=['confidence_score']),
        ]
        ordering = ['-processed_at']

    def __str__(self):
        return self.title

class ReportSection(models.Model):
    """
    Model to store structured sections of reports for targeted querying
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(GeologicalReport, on_delete=models.CASCADE, related_name='sections')
    
    # Section metadata
    section_type = models.CharField(max_length=100)  # e.g., 'geology', 'mineralization', 'conclusions'
    section_title = models.CharField(max_length=255, blank=True)
    section_order = models.IntegerField(default=0)
    
    # Content
    content = models.TextField()
    summary = models.TextField(blank=True)
    
    # Structured data extracted from this section
    extracted_data = models.JSONField(default=dict)  # Coordinates, minerals, formations, etc.
    
    # Search optimization
    keywords = models.JSONField(default=list)
    entities = models.JSONField(default=list)  # Named entities found in section
    
    class Meta:
        indexes = [
            models.Index(fields=['section_type']),
            models.Index(fields=['section_order']),
            models.Index(fields=['keywords']),
        ]
        ordering = ['report', 'section_order']

    def __str__(self):
        return f"{self.report.title} - {self.section_type}"

class ReportQuery(models.Model):
    """
    Model to store and track LLM queries against reports
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Query details
    user_query = models.TextField()
    query_type = models.CharField(max_length=50)  # e.g., 'location_search', 'mineral_search', 'general'
    
    # Results
    relevant_reports = models.ManyToManyField(GeologicalReport, related_name='queries')
    relevant_sections = models.ManyToManyField(ReportSection, related_name='queries')
    
    # Response
    llm_response = models.TextField()
    confidence_score = models.FloatField(default=0.0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(default=0.0)  # Time taken to process query
    
    class Meta:
        indexes = [
            models.Index(fields=['query_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['confidence_score']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Query: {self.user_query[:50]}..."

class ReportIndex(models.Model):
    """
    Model to store searchable index of report content for fast retrieval
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(GeologicalReport, on_delete=models.CASCADE, related_name='indices')
    
    # Indexed content
    indexed_text = models.TextField()  # Preprocessed text for search
    vector_embedding = models.JSONField(default=list)  # Vector embedding for semantic search
    
    # Search metadata
    word_frequencies = models.JSONField(default=dict)  # Term frequency for keyword search
    entity_index = models.JSONField(default=dict)  # Named entities and their locations
    
    # Index metadata
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['last_updated']),
        ]

    def __str__(self):
        return f"Index for {self.report.title}"

class ConversationSession(models.Model):
    """
    Model to store conversation sessions for user interaction tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=255, unique=True)  # Browser session ID
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Analysis mode tracking
    analysis_mode = models.CharField(max_length=20, default='smart')
    documents_used = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_activity']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-last_activity']

    def __str__(self):
        return f"Session {self.session_id} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class ConversationMessage(models.Model):
    """
    Model to store individual messages in conversations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='messages')
    
    # Message details
    role = models.CharField(max_length=20, choices=[
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System')
    ])
    content = models.TextField()
    
    # Query analysis
    query_type = models.CharField(max_length=50, blank=True)  # e.g., 'geological', 'general', 'location_search'
    confidence_score = models.FloatField(default=0.0)
    analysis_mode = models.CharField(max_length=20, default='smart')
    
    # Data source tracking
    documents_referenced = models.JSONField(default=list)  # List of document IDs used
    data_sources_used = models.JSONField(default=list)  # List of data sources used
    
    # Response metadata
    response_time = models.FloatField(default=0.0)  # Time taken to generate response
    tokens_used = models.IntegerField(default=0)
    model_used = models.CharField(max_length=50, default='gpt-4o')
    

    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['role']),
            models.Index(fields=['query_type']),
            models.Index(fields=['analysis_mode']),
        ]
        ordering = ['session', 'created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}... ({self.created_at.strftime('%H:%M')})"

class UserInteraction(models.Model):
    """
    Model to track user interactions and learning patterns
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='interactions')
    
    # Interaction details
    interaction_type = models.CharField(max_length=50, choices=[
        ('query', 'Query'),
        ('feedback', 'Feedback'),
        ('mode_switch', 'Analysis Mode Switch'),
        ('document_upload', 'Document Upload'),
        ('error', 'Error'),
        ('success', 'Success')
    ])
    
    # Context
    context_data = models.JSONField(default=dict)  # Additional context data
    user_preferences = models.JSONField(default=dict)  # User preferences and settings
    
    # Learning data
    query_patterns = models.JSONField(default=list)  # Common query patterns
    preferred_topics = models.JSONField(default=list)  # Topics user frequently asks about
    response_satisfaction = models.FloatField(default=0.0)  # Average satisfaction score
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['interaction_type']),
            models.Index(fields=['response_satisfaction']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.interaction_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

