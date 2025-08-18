from django.urls import path
from . import views
from . import unified_chat_views

urlpatterns = [
    path('', views.index, name='home'),
    path('create-account/', views.create_account, name='create-account'),
    path('maps/', views.maps, name='maps'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('predict/', views.predict, name='predict'),
    path('intelligent-predictions/', views.intelligent_predictions, name='intelligent-predictions'),
    path('dataset/', views.dataset_view, name='dataset'),
    path('api/predict/', views.make_prediction, name='make-prediction'),
    path('api/history/', views.prediction_history, name='prediction-history'),
    path('api/train/', views.train_model, name='train-model'),
    path('api/process-survey/', views.process_survey_data, name='process-survey'),
    path('api/feature-importance/', views.get_feature_importance, name='feature-importance'),
    path('api/check-duplicates/', views.check_duplicates, name='check-duplicates'),
    path('geological-survey-results/', views.get_geological_survey_results, name='geological_survey_results'),
    path('api/geological-surveys/', views.geological_survey_list, name='geological_survey_list'),
    path('api/get-data-quality-metrics/', views.get_data_quality_metrics, name='get_data_quality_metrics'),
    path('api/gold-price/', views.get_gold_price, name='get-gold-price'),
    
    # File upload endpoints
    path('upload-file/', views.upload_file, name='upload-file'),
    path('process-file/<uuid:upload_id>/', views.process_file, name='process-file'),
    path('api/process-file/<uuid:upload_id>/', views.process_file, name='api-process-file'),
    path('api/file-status/<uuid:upload_id>/', views.get_file_status_api, name='get-file-status-api'),
    path('get-files/', views.get_files, name='get-files'),
    path('delete-file/<uuid:upload_id>/', views.delete_file, name='delete-file'),
    path('api/extracted-text-files/', views.get_extracted_text_files, name='get-extracted-text-files'),
    path('api/advanced-search/', views.advanced_search_documents, name='advanced-search-documents'),
    
    # Upload management endpoints
    path('upload-management/', views.upload_management, name='upload_management'),
    path('api/cancel-processing/<str:upload_id>/', views.cancel_processing, name='cancel_processing'),
    path('api/retry-processing/<str:upload_id>/', views.retry_processing, name='retry_processing'),
    
    # Unified Chat endpoints (replaces both old chat systems)
    path('api/unified-chat/', unified_chat_views.unified_chat, name='unified-chat'),
    path('api/unified-chat/status/', unified_chat_views.get_unified_chat_status, name='unified-chat-status'),
    path('api/unified-chat/history/<str:session_id>/', unified_chat_views.get_conversation_history, name='unified-chat-history'),
    path('api/unified-chat/clear/<str:session_id>/', unified_chat_views.clear_conversation_history, name='unified-chat-clear'),
]