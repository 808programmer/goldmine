import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def process_dataset(file_path, dataset_name=None):
    """
    Process an uploaded dataset and return the processed DataFrame
    
    Args:
        file_path (str): Path to the dataset file
        dataset_name (str): Name of the dataset (for logging)
        
    Returns:
        tuple: processed DataFrame, row count
    """
    try:
        # Determine file type from extension
        extension = file_path.split('.')[-1].lower()
        
        # Read file into DataFrame
        if extension == 'csv':
            df = pd.read_csv(file_path)
        elif extension in ['xls', 'xlsx']:
            df = pd.read_excel(file_path)
        else:
            logger.error(f"Unsupported file format: {extension}")
            return None, 0
        
        # Check for required columns
        required_columns = ['latitude', 'longitude', 'elevation', 'soil_type', 'geological_formation']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Dataset {dataset_name} missing required columns: {missing_columns}")
            return None, 0
        
        # Check if 'gold_present' column exists, if not add a dummy column
        # This allows uploading data without labels for predictions
        if 'gold_present' not in df.columns:
            logger.warning(f"Dataset {dataset_name} has no 'gold_present' column. Adding dummy values.")
            df['gold_present'] = np.nan
        
        # Basic data cleaning
        # Convert coordinates to numeric
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['elevation'] = pd.to_numeric(df['elevation'], errors='coerce')
        
        # Drop rows with invalid coordinates
        initial_rows = len(df)
        df = df.dropna(subset=['latitude', 'longitude', 'elevation'])
        if len(df) < initial_rows:
            logger.warning(f"Dropped {initial_rows - len(df)} rows with invalid coordinates")
        
        # Check if there's still data after cleaning
        if len(df) == 0:
            logger.error(f"No valid data after cleaning dataset {dataset_name}")
            return None, 0
        
        # Standardize categorical values
        df['soil_type'] = df['soil_type'].str.lower()
        df['geological_formation'] = df['geological_formation'].str.lower()
        
        # Replace any non-standard values with the most common ones
        standard_soil_types = ['alluvial', 'laterite', 'sandy', 'clay']
        standard_formations = ['greenstone', 'granite', 'sedimentary', 'metamorphic']
        
        df['soil_type'] = df['soil_type'].apply(
            lambda x: x if x in standard_soil_types else standard_soil_types[0]
        )
        
        df['geological_formation'] = df['geological_formation'].apply(
            lambda x: x if x in standard_formations else standard_formations[0]
        )
        
        logger.info(f"Successfully processed dataset {dataset_name} with {len(df)} rows")
        return df, len(df)
    
    except Exception as e:
        logger.error(f"Error processing dataset {dataset_name}: {str(e)}")
        return None, 0 