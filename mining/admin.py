from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Miner, PDFTextData, GeologicalSurvey, GeologicalFeature, 
    MineralDeposit, SoilAnalysis, PredictionHistory, TrainingRecord, UploadedFile
)

@admin.register(PDFTextData)
class PDFTextDataAdmin(admin.ModelAdmin):
    list_display = [
        'filename', 'original_filename', 'file_size_display', 
        'is_processed', 'created_at', 'duplicate_status'
    ]
    list_filter = [
        'is_processed', 'created_at', 'processed_at', 'is_large_file'
    ]
    search_fields = ['filename', 'original_filename', 'extracted_text']
    readonly_fields = [
        'id', 'created_at', 'processed_at', 'file_hash', 'content_hash', 
        'file_size', 'duplicate_status', 'duplicate_details'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('filename', 'original_filename', 'file_size', 'created_at')
        }),
        ('Content', {
            'fields': ('extracted_text', 'processed_text', 'text_file_path')
        }),
        ('Processing Status', {
            'fields': ('is_processed', 'processed_at', 'is_large_file')
        }),
        ('Duplicate Detection', {
            'fields': ('file_hash', 'content_hash', 'duplicate_status', 'duplicate_details'),
            'classes': ('collapse',)
        }),
        ('Relations', {
            'fields': ('dataset',),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size:,} bytes"
        return "N/A"
    file_size_display.short_description = "File Size"
    
    def duplicate_status(self, obj):
        if obj.is_duplicate():
            duplicates = obj.get_duplicate_info()
            if duplicates:
                severity = 'high' if any(d.get('type') == 'file_hash' for d in duplicates) else 'medium'
                color = 'red' if severity == 'high' else 'orange'
                return format_html(
                    '<span style="color: {}; font-weight: bold;">DUPLICATE ({})</span>',
                    color, len(duplicates)
                )
        return format_html('<span style="color: green;">UNIQUE</span>')
    duplicate_status.short_description = "Duplicate Status"
    
    def duplicate_details(self, obj):
        if obj.is_duplicate():
            duplicates = obj.get_duplicate_info()
            if duplicates:
                details = []
                for dup in duplicates:
                    details.append(
                        f"• {dup['reason']}: {dup['document'].filename} "
                        f"(ID: {dup['document'].id})"
                    )
                return mark_safe('<br>'.join(details))
        return "No duplicates found"
    duplicate_details.short_description = "Duplicate Details"
    
    actions = ['mark_as_processed', 'mark_as_unprocessed', 'show_duplicates']
    
    def mark_as_processed(self, request, queryset):
        updated = queryset.update(is_processed=True)
        self.message_user(request, f"{updated} documents marked as processed.")
    mark_as_processed.short_description = "Mark selected documents as processed"
    
    def mark_as_unprocessed(self, request, queryset):
        updated = queryset.update(is_processed=False)
        self.message_user(request, f"{updated} documents marked as unprocessed.")
    mark_as_unprocessed.short_description = "Mark selected documents as unprocessed"
    
    def show_duplicates(self, request, queryset):
        duplicate_count = 0
        for obj in queryset:
            if obj.is_duplicate():
                duplicate_count += 1
        
        self.message_user(
            request, 
            f"Found {duplicate_count} documents with duplicates out of {queryset.count()} selected."
        )
    show_duplicates.short_description = "Show duplicate information for selected documents"

@admin.register(GeologicalSurvey)
class GeologicalSurveyAdmin(admin.ModelAdmin):
    list_display = ['survey_id', 'title', 'location', 'survey_date', 'author', 'created_at']
    list_filter = ['survey_date', 'location', 'created_at']
    search_fields = ['survey_id', 'title', 'location', 'author', 'description']
    readonly_fields = ['id', 'created_at']

@admin.register(GeologicalFeature)
class GeologicalFeatureAdmin(admin.ModelAdmin):
    list_display = [
        'feature_type', 'name', 'latitude', 'longitude', 'elevation', 
        'confidence_score', 'gold_probability', 'created_at'
    ]
    list_filter = ['feature_type', 'confidence_score', 'gold_probability', 'created_at']
    search_fields = ['name', 'description', 'feature_type']
    readonly_fields = ['id', 'created_at']

@admin.register(MineralDeposit)
class MineralDepositAdmin(admin.ModelAdmin):
    list_display = [
        'mineral_type', 'concentration', 'depth', 'estimated_quantity', 
        'extraction_difficulty', 'created_at'
    ]
    list_filter = ['mineral_type', 'extraction_difficulty', 'created_at']
    search_fields = ['mineral_type']

@admin.register(SoilAnalysis)
class SoilAnalysisAdmin(admin.ModelAdmin):
    list_display = ['soil_type', 'ph_level', 'organic_matter', 'created_at']
    list_filter = ['soil_type', 'created_at']
    search_fields = ['soil_type', 'mineral_content']

@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'mineral_type', 'latitude', 'longitude', 'probability', 'confidence', 
        'soil_type', 'geological_formation', 'created_at'
    ]
    list_filter = ['mineral_type', 'soil_type', 'geological_formation', 'created_at']
    search_fields = ['mineral_type', 'soil_type', 'geological_formation']
    readonly_fields = ['id', 'created_at']

@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ['accuracy', 'model_path', 'training_date']
    list_filter = ['training_date', 'accuracy']
    readonly_fields = ['id', 'training_date']

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'status', 'uploaded_at']
    list_filter = ['status', 'uploaded_at']
    search_fields = ['filename']
    readonly_fields = ['id', 'uploaded_at']

# Register your models here.
admin.site.register(Miner)