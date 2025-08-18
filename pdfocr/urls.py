from django.urls import path
from pdfocr import views

app_name = 'pdfocr'

urlpatterns = [
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('status/<uuid:upload_id>/', views.get_upload_status, name='get_upload_status'),
    path('history/', views.upload_history, name='upload_history'),
    path('user-uploads/', views.user_pdf_uploads, name='user_pdf_uploads'),
    path('upload-file/', views.upload_file_only, name='upload_file_only'),
    path('upload-multiple/', views.upload_multiple_files, name='upload_multiple_files'),
    path('process-file/<uuid:upload_id>/', views.process_uploaded_file, name='process_uploaded_file'),
    path('process-direct/', views.process_file_direct, name='process_file_direct'),
    path('test-credentials/', views.test_adobe_credentials, name='test_adobe_credentials'),
    path('debug-account/', views.debug_adobe_account, name='debug_adobe_account'),
]