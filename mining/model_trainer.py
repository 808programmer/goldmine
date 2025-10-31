import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
import joblib
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def preprocess_data(df):
    """
    Preprocess the data for training with advanced feature engineering
    
    Args:
        df (pandas.DataFrame): The dataset to preprocess
        
    Returns:
        tuple: X, y, feature_names, encoders, scaler
    """
    # Check for required columns
    required_columns = ['latitude', 'longitude', 'elevation', 'soil_type', 'geological_formation', 'gold_present']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.error(f"Missing required columns: {missing_columns}")
        return None
    
    # Feature engineering
    # Create a copy to avoid modifying the original dataframe
    df_processed = df.copy()
    
    # Normalize coordinates to be distances from region center (useful for hotspot modeling)
    region_center_lat = 4.9  # Center of Potaro-Siparuni region
    region_center_lon = -59.0
    df_processed['dist_from_center'] = np.sqrt(
        (df_processed['latitude'] - region_center_lat)**2 + 
        (df_processed['longitude'] - region_center_lon)**2
    )
    
    # Add elevation bands as this can be more predictive than raw elevation
    df_processed['elevation_band'] = pd.cut(
        df_processed['elevation'], 
        bins=[0, 500, 1000, 1500, 2000], 
        labels=['low', 'medium', 'high', 'very_high']
    )
    
    # Create interaction features
    # Some soil types are more likely to have gold at certain elevations
    soil_dummies = pd.get_dummies(df_processed['soil_type'], prefix='soil')
    elevation_dummies = pd.get_dummies(df_processed['elevation_band'], prefix='elev')
    
    # Combine soil and elevation interaction features
    for soil_col in soil_dummies.columns:
        for elev_col in elevation_dummies.columns:
            df_processed[f"{soil_col}_{elev_col}"] = soil_dummies[soil_col] * elevation_dummies[elev_col]
    
    # Prepare features and target
    # Basic features
    basic_features = ['latitude', 'longitude', 'elevation']
    
    # Engineered features
    engineered_features = ['dist_from_center']
    
    # Categorical features (will be one-hot encoded)
    categorical_features = ['soil_type', 'geological_formation', 'elevation_band']
    
    # All features together
    feature_names = basic_features + engineered_features + categorical_features
    
    # Extract features and target
    X = df_processed[feature_names].copy()
    y = df_processed['gold_present'].copy()
    
    # Handle categorical variables with one-hot encoding
    # This is now handled in the pipeline, but we still need encoders for prediction
    label_encoders = {}
    for column in ['soil_type', 'geological_formation']:
        encoder = LabelEncoder()
        # Just fit the encoder for future use, don't transform now
        encoder.fit(df_processed[column])
        label_encoders[column] = encoder
    
    # Prepare categorical feature indices for the ColumnTransformer
    categorical_indices = [feature_names.index(f) for f in categorical_features]
    
    # Create preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), [i for i in range(len(feature_names)) if i not in categorical_indices]),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_indices)
        ]
    )
    
    # Return the data and preprocessing objects
    return X, y, feature_names, label_encoders, preprocessor

def train_model(X, y, preprocessor):
    """
    Train a model for gold prediction with hyperparameter tuning and cross-validation
    
    Args:
        X (pandas.DataFrame): Features
        y (numpy.ndarray): Target
        preprocessor (ColumnTransformer): Preprocessing pipeline
        
    Returns:
        tuple: best_model, accuracy, metrics
    """
    # Create full pipeline including preprocessing and model
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(random_state=42))
    ])
    
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', GradientBoostingClassifier(random_state=42))
    ])
    
    # Define hyperparameter grids for both models
    rf_param_grid = {
        'classifier__n_estimators': [100, 200, 300],
        'classifier__max_depth': [None, 10, 20, 30],
        'classifier__min_samples_split': [2, 5, 10],
        'classifier__min_samples_leaf': [1, 2, 4],
        'classifier__class_weight': [None, 'balanced']
    }
    
    gb_param_grid = {
        'classifier__n_estimators': [100, 200, 300],
        'classifier__learning_rate': [0.01, 0.1, 0.2],
        'classifier__max_depth': [3, 5, 7],
        'classifier__min_samples_split': [2, 5, 10],
        'classifier__min_samples_leaf': [1, 2, 4]
    }
    
    # Split data for training and testing
    if len(X) < 5:
        # If we have very few samples, use all data for training
        X_train, X_test, y_train, y_test = X, X, y, y
        logger.warning("Very few samples available, using all data for training")
    else:
        # Check if we have enough classes for stratification
        unique_classes = len(np.unique(y))
        if unique_classes < 2:
            logger.warning("Only one class found in target variable - cannot use stratification")
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        else:
            # Normal split with stratification
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Create and train GridSearchCV for RandomForest
    logger.info("Starting RandomForest hyperparameter tuning...")
    
    # Handle very small datasets or single class
    unique_classes = len(np.unique(y_train))
    if len(X_train) < 2 or unique_classes < 2:
        if len(X_train) < 2:
            logger.warning("Only 1 sample available - skipping cross-validation and using default parameters")
        else:
            logger.warning("Only 1 class available - cannot train classification model")
            return None, 0.0, {'error': 'Only one class found in training data'}
        
        # Use default parameters without cross-validation
        rf_model = rf_pipeline.set_params(**{
            'classifier__n_estimators': 100,
            'classifier__max_depth': 10,
            'classifier__min_samples_split': 2,
            'classifier__min_samples_leaf': 1,
            'classifier__class_weight': None
        })
        rf_model.fit(X_train, y_train)
        rf_best_model = rf_model
        rf_best_score = 1.0  # Perfect score for single sample
    else:
        # Adjust CV folds based on sample size and class distribution
        unique_classes_train = len(np.unique(y_train))
        min_class_count = min([np.sum(y_train == cls) for cls in np.unique(y_train)]) if unique_classes_train >= 2 else len(y_train)
        
        # Calculate appropriate CV folds based on smallest class
        # CV folds cannot exceed the number of samples in the smallest class
        if min_class_count < 2:
            # If a class has only 1 sample, we can't use CV - skip it
            logger.warning(f"Smallest class has only {min_class_count} sample(s) - skipping cross-validation, using default parameters")
            rf_model = rf_pipeline.set_params(**{
                'classifier__n_estimators': 100,
                'classifier__max_depth': 10,
                'classifier__min_samples_split': 2,
                'classifier__min_samples_leaf': 1,
                'classifier__class_weight': 'balanced'
            })
            rf_model.fit(X_train, y_train)
            rf_best_model = rf_model
            rf_best_score = 1.0
        elif min_class_count == 2:
            # Minimum for CV - use 2 folds
            cv_folds = 2
            logger.warning(f"Using {cv_folds} folds due to small sample size (min class: {min_class_count} samples)")
        elif len(X_train) < 5:
            # Small dataset but enough per class
            cv_folds = min(2, min_class_count)
            logger.warning(f"Using {cv_folds} folds due to small sample size")
        else:
            # Normal case - use up to 5 folds but not more than smallest class
            cv_folds = min(5, min_class_count)
            logger.info(f"Using {cv_folds} folds for cross-validation")
        
        # Only proceed with GridSearchCV if we didn't already fit a model above
        if min_class_count >= 2:
            rf_grid_search = GridSearchCV(
                rf_pipeline, 
                rf_param_grid, 
                cv=cv_folds, 
                scoring='f1',
                n_jobs=-1,
                verbose=1
            )
            rf_grid_search.fit(X_train, y_train)
            rf_best_model = rf_grid_search.best_estimator_
            rf_best_score = rf_grid_search.best_score_
    
    # Create and train GridSearchCV for GradientBoosting
    logger.info("Starting GradientBoosting hyperparameter tuning...")
    
    if len(X_train) < 2:
        logger.warning("Only 1 sample available - skipping cross-validation for GradientBoosting")
        # Use default parameters without cross-validation
        gb_model = gb_pipeline.set_params(**{
            'classifier__n_estimators': 100,
            'classifier__learning_rate': 0.1,
            'classifier__max_depth': 3,
            'classifier__min_samples_split': 2,
            'classifier__min_samples_leaf': 1
        })
        gb_model.fit(X_train, y_train)
        gb_best_model = gb_model
        gb_best_score = 1.0  # Perfect score for single sample
    else:
        # Use same CV folds for GradientBoosting
        gb_grid_search = GridSearchCV(
            gb_pipeline,
            gb_param_grid,
            cv=cv_folds,
            scoring='f1',
            n_jobs=-1,
            verbose=1
        )
        gb_grid_search.fit(X_train, y_train)
        gb_best_model = gb_grid_search.best_estimator_
        gb_best_score = gb_grid_search.best_score_
    
    # Choose the best model between RF and GB
    if rf_best_model is None or gb_best_model is None:
        logger.error("Model training failed - insufficient data or classes")
        return None, 0.0, {'error': 'Model training failed due to insufficient data'}
    
    if rf_best_score > gb_best_score:
        best_model = rf_best_model
        logger.info(f"RandomForest selected as best model with CV F1 score: {rf_best_score:.4f}")
    else:
        best_model = gb_best_model
        logger.info(f"GradientBoosting selected as best model with CV F1 score: {gb_best_score:.4f}")
    
    # Validate that we have a valid model before proceeding
    if best_model is None:
        logger.error("No valid model was created")
        return None, 0.0, {'error': 'No valid model was created'}
    
    # Get predictions on test set
    y_pred = best_model.predict(X_test)
    y_pred_proba = best_model.predict_proba(X_test)[:, 1]
    
    # Calculate various metrics
    if len(X) < 5:
        # For very few samples, use training metrics
        y_train_pred = best_model.predict(X_train)
        y_train_pred_proba = best_model.predict_proba(X_train)[:, 1]
        metrics = {
            'accuracy': accuracy_score(y_train, y_train_pred),
            'f1_score': f1_score(y_train, y_train_pred),
            'precision': precision_score(y_train, y_train_pred),
            'recall': recall_score(y_train, y_train_pred),
            'roc_auc': roc_auc_score(y_train, y_train_pred_proba)
        }
        logger.warning("Using training metrics due to insufficient test data")
    else:
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba)
        }
    
    logger.info(f"Model evaluation metrics:")
    for metric_name, metric_value in metrics.items():
        logger.info(f"{metric_name}: {metric_value:.4f}")
    
    # Also calculate cross-validation scores on entire dataset
    if len(X) < 2:
        logger.warning("Skipping cross-validation due to insufficient samples")
        cv_mean = 1.0
        cv_std = 0.0
        logger.info("Cross-validation skipped - using training accuracy")
    else:
        cv_folds_final = min(5, len(X))
        if cv_folds_final < 2:
            cv_folds_final = 2
        cv_scores = cross_val_score(best_model, X, y, cv=cv_folds_final, scoring='f1')
        cv_mean = np.mean(cv_scores)
        cv_std = np.std(cv_scores)
        logger.info(f"{cv_folds_final}-fold cross-validation F1 score: {cv_mean:.4f} (±{cv_std:.4f})")
    
    return best_model, metrics['accuracy'], metrics

def train_model_from_dataset(dataset):
    """
    Train a model from a dataset file
    
    Args:
        dataset (Dataset): Dataset model instance
        
    Returns:
        dict: Training results
    """
    try:
        # Read the dataset
        file_path = dataset.file.path
        extension = file_path.split('.')[-1].lower()
        
        if extension == 'csv':
            df = pd.read_csv(file_path)
        elif extension in ['xls', 'xlsx']:
            df = pd.read_excel(file_path)
        else:
            logger.error(f"Unsupported file format: {extension}")
            return {'success': False, 'error': f'Unsupported file format: {extension}'}
        
        # Preprocess data
        preprocess_result = preprocess_data(df)
        if preprocess_result is None:
            return {'success': False, 'error': 'Preprocessing failed or missing required columns'}
            
        X, y, feature_names, label_encoders, preprocessor = preprocess_result
        
        # Fit the preprocessor on the training data
        preprocessor.fit(X, y)
        
        # Train model
        model, accuracy, metrics = train_model(X, y, preprocessor)
        
        # Save the model and preprocessing objects
        model_dir = Path('mining/models')
        os.makedirs(model_dir, exist_ok=True)
        
        # Save with filenames expected by the loader
        model_path = model_dir / 'mineral_prediction_model.joblib'
        scaler_path = model_dir / 'mineral_scaler.joblib'
        encoders_path = model_dir / 'mineral_encoders.joblib'
        preprocessor_path = model_dir / 'preprocessor.joblib'
        
        joblib.dump(model, model_path)
        # Save the scaler and encoders if available
        if preprocessor and hasattr(preprocessor, 'named_transformers_'):
            # Try to extract the scaler from the pipeline
            try:
                scaler = preprocessor.named_transformers_['num']
                joblib.dump(scaler, scaler_path)
            except Exception as e:
                logger.warning(f"Could not save scaler: {e}")
        else:
            logger.warning("Preprocessor has no named_transformers_ attribute; scaler not saved.")
        joblib.dump(label_encoders, encoders_path)
        # Save the fitted preprocessor
        if preprocessor:
            joblib.dump(preprocessor, preprocessor_path)
        
        logger.info(f"Model and preprocessing objects saved to {model_dir}")
        
        # Save additional model metadata
        metadata = {
            'feature_names': feature_names,
            'metrics': metrics,
            'dataset_name': dataset.name,
            'dataset_id': dataset.id,
            'model_type': type(model.named_steps['classifier']).__name__
        }
        metadata_path = model_dir / 'model_metadata.joblib'
        joblib.dump(metadata, metadata_path)
        
        return {
            'success': True,
            'test_accuracy': float(accuracy),
            'test_f1': float(metrics['f1_score']),
            'model_path': str(model_path),
            'feature_names': feature_names,
            'model_type': metadata['model_type']
        }
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return {'success': False, 'error': str(e)} 