from django.urls import path
from . import views
from . import unified_chat_views

urlpatterns = [
    path('', views.index, name='home'),
    path('create-account/', views.create_account, name='create-account'),
    path('maps/', views.maps, name='maps'),
    path('map-test/', views.map_test, name='map-test'),
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
    
    # Mineralization trends and training status endpoints
    path('api/mineralization-trends/', views.get_mineralization_trends, name='mineralization-trends'),
    path('api/openai-training-status/', views.get_openai_training_status, name='openai-training-status'),
    
    # Enhanced predictions and intelligent analysis endpoints
    path('api/enhanced-predictions/', views.get_enhanced_predictions, name='enhanced-predictions'),
    path('api/intelligent-predictions-status/', views.get_intelligent_predictions_status, name='intelligent-predictions-status'),
    path('api/generate-intelligent-coordinates/', views.generate_intelligent_coordinates, name='generate-intelligent-coordinates'),
    path('api/generate-intelligent-coordinates-from-source/', views.generate_intelligent_coordinates_from_source, name='generate-intelligent-coordinates-from-source'),
    path('api/generate-intelligent-trends/', views.generate_intelligent_trends, name='generate-intelligent-trends'),
    path('api/analyze-texts-for-map/', views.analyze_texts_for_map, name='analyze-texts-for-map'),
    path('api/map-coordinates/', views.get_map_coordinates, name='map-coordinates'),
    path('api/analyze-historical-prospects/', views.analyze_historical_prospects, name='analyze-historical-prospects'),
    path('api/intelligent-coordinates/', views.get_intelligent_coordinates, name='intelligent-coordinates'),
    
    # Model prediction endpoints
    path('api/generate-predictions/', views.generate_model_predictions, name='generate-model-predictions'),
    path('api/clear-predictions/', views.clear_model_predictions, name='clear-model-predictions'),

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

    path('simple-mapping/', views.simple_intelligent_mapping, name='simple-intelligent-mapping'),
    path('api/simple-intelligent-coordinates/', views.api_simple_intelligent_coordinates, name='api-simple-intelligent-coordinates'),
    path('health/', views.health_check, name='health_check'),
    
    # Training Management & Status API endpoints
    path('api/training-status/', views.get_training_status, name='training-status'),
    path('api/validation-status/', views.get_validation_status, name='validation-status'),
    path('api/trigger-training/', views.trigger_manual_training, name='trigger-training'),
    path('api/model-versions/', views.list_model_versions, name='model-versions'),
    path('api/activate-model-version/', views.activate_model_version, name='activate-model-version'),
    path('api/training-progress/', views.get_training_progress, name='training-progress'),
]