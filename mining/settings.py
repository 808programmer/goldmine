# Mining App Settings

# Automated Training Configuration
AUTO_TRAIN_ON_PDF_UPLOAD = True # Enable/disable automatic training when PDFs are uploaded
AUTO_TRAIN_MIN_FILES = 1  # Minimum number of unprocessed files before triggering training
AUTO_TRAIN_DELAY_SECONDS = 2  # Delay before starting training (to ensure file is saved)

# LLM Configuration
LLM_MODEL = "gpt-4o-mini"  # Default LLM model to use
LLM_TEMPERATURE = 0.1  # Temperature for LLM responses
LLM_MAX_TOKENS = 200000  # Maximum tokens for LLM responses

# Training Configuration
TRAINING_TEST_SIZE = 0.2  # Test set size for model training
TRAINING_RANDOM_STATE = 42  # Random state for reproducible results
TRAINING_CV_FOLDS = 5  # Number of cross-validation folds

# Model Storage
MODEL_STORAGE_PATH = "mining/models/"  # Path to store trained models
DATASET_STORAGE_PATH = "media/datasets/"  # Path to store training datasets 