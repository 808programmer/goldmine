#!/bin/bash

# GoldMine AI Model Training Script
# This script trains the model directly from the extracted_texts folder

echo "🎯 GoldMine AI - Model Training"
echo "=================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Please run this script from the project root directory (where manage.py is located)"
    exit 1
fi

# Check if extracted_texts folder exists
if [ ! -d "media/extracted_texts" ]; then
    echo "❌ media/extracted_texts folder not found"
    echo "   Please ensure you have extracted text files in the media/extracted_texts folder"
    exit 1
fi

# Count text files
TEXT_COUNT=$(find media/extracted_texts -name "*.txt" | wc -l)
echo "📚 Found $TEXT_COUNT text files in media/extracted_texts"

if [ $TEXT_COUNT -eq 0 ]; then
    echo "❌ No text files found. Please add some .txt files to media/extracted_texts first"
    exit 1
fi

# Function to show usage
show_usage() {
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --status          Check current training status only"
    echo "  --limit N         Process maximum N text files"
    echo "  --force           Force retraining (overwrite existing model)"
    echo "  --verbose         Enable verbose output"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Train from all text files"
    echo "  $0 --status           # Check status only"
    echo "  $0 --limit 50         # Train from max 50 text files"
    echo "  $0 --force            # Force retraining"
    echo "  $0 --limit 100 --force # Train from max 100 files, force retrain"
    echo ""
}

# Parse command line arguments
LIMIT=""
FORCE=""
VERBOSE=""
STATUS_ONLY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --limit)
            LIMIT="--limit $2"
            shift 2
            ;;
        --force)
            FORCE="--force"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --status)
            STATUS_ONLY="--status"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Run the training script
echo ""
echo "🚀 Starting training process..."
echo "   Command: python3 batch_train.py $STATUS_ONLY $LIMIT $FORCE $VERBOSE"
echo ""

python3 batch_train.py $STATUS_ONLY $LIMIT $FORCE $VERBOSE

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Training completed successfully!"
else
    echo ""
    echo "❌ Training failed. Check the logs above for details."
    exit 1
fi
