"""
AI Training Agent
An intelligent agent that orchestrates the entire training pipeline with reasoning.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from openai import OpenAI

from .training_data_validator import TrainingDataValidator
from .training_status_service import TrainingStatusService
from .automated_training_service import AutomatedTrainingService
from .llm_model_trainer import LLMModelTrainer
from .model_versioning import ModelVersionManager
from .models import PDFTextData, ModelVersion

logger = logging.getLogger(__name__)


class TrainingAgent:
    """
    AI Agent that intelligently manages the training pipeline.
    
    This agent uses OpenAI to reason about the training process and make
    intelligent decisions about when and how to train the model.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the training agent
        
        Args:
            api_key: OpenAI API key (uses settings if not provided)
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
        # Initialize services
        self.validator = TrainingDataValidator()
        self.status_service = TrainingStatusService()
        self.auto_training_service = AutomatedTrainingService()
        self.llm_trainer = LLMModelTrainer()
        self.version_manager = ModelVersionManager()
    
    def analyze_situation(self) -> Dict:
        """
        Analyze the current training situation and recommend actions
        
        Returns:
            Dictionary with analysis and recommendations
        """
        try:
            # Gather current system state
            status = self.status_service.get_comprehensive_status()
            validation = self.validator.validate_all_requirements()
            
            # Check if OpenAI is available for reasoning
            if not self.client:
                logger.warning("OpenAI not available - using basic reasoning")
                return self._basic_analysis(status, validation)
            
            # Use AI to analyze the situation
            prompt = self._create_analysis_prompt(status, validation)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI training agent for a gold prediction machine learning system. "
                            "Analyze the training situation and recommend the best course of action. "
                            "Respond with JSON containing your analysis and recommendations."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse AI response
            analysis = self._parse_ai_analysis(response.choices[0].message.content)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            status = self.status_service.get_comprehensive_status()
            validation = self.validator.validate_all_requirements()
            return self._basic_analysis(status, validation)
    
    def _create_analysis_prompt(self, status: Dict, validation: Dict) -> str:
        """Create prompt for AI analysis"""
        return f"""
Analyze the current state of the gold prediction model training system and recommend actions.

CURRENT SYSTEM STATE:
{self._format_status(status)}

DATA VALIDATION STATUS:
{self._format_validation(validation)}

LATEST MODEL VERSION:
{self._format_latest_model()}

TASK: Analyze this situation and provide:
1. Should we train now? (yes/no with reason)
2. What's the best training strategy? (full/incremental/minimal)
3. Any issues or warnings?
4. Recommended next steps

Respond in JSON format:
{{
    "should_train": boolean,
    "reason": "string explaining why",
    "strategy": "full|incremental|minimal",
    "strategy_reason": "string explaining strategy choice",
    "issues": ["list of issues"],
    "warnings": ["list of warnings"],
    "recommendations": ["list of recommended actions"],
    "confidence": float (0.0 to 1.0)
}}
"""
    
    def _format_status(self, status: Dict) -> str:
        """Format status for prompt"""
        upload = status.get('upload_status', {})
        training = status.get('training_status', {})
        validation = status.get('validation_status', {})
        
        return f"""
- Total documents: {upload.get('total_documents', upload.get('total', 0))}
- Processed documents: {upload.get('processed_documents', upload.get('processed', 0))}
- Extracted text files: {validation.get('document_count', 0)}
- Training status: {training.get('status', 'unknown')}
- Last training: {training.get('last_training_date', 'never')}
"""
    
    def _format_validation(self, validation: Dict) -> str:
        """Format validation for prompt"""
        return f"""
- Ready for training: {validation.get('ready_for_training', False)}
- Quality score: {validation.get('quality_score', validation.get('metrics', {}).get('overall_quality_score', 0)):.2f}
- Document count: {validation.get('document_count', 0)}
- Issues: {len(validation.get('issues', validation.get('errors', [])))}
- Warnings: {len(validation.get('warnings', []))}
"""
    
    def _format_latest_model(self) -> str:
        """Format latest model info"""
        latest = self.version_manager.get_latest_version()
        if latest:
            return f"""
- Version: {latest.version_number}
- Accuracy: {latest.accuracy:.3f}
- Trained: {latest.trained_at}
- Active: {latest.is_active}
"""
        return "No previous training"
    
    def _parse_ai_analysis(self, content: str) -> Dict:
        """Parse AI analysis response"""
        import json
        try:
            analysis = json.loads(content)
            
            # Ensure required fields
            analysis.setdefault('should_train', False)
            analysis.setdefault('reason', 'Not analyzed')
            analysis.setdefault('strategy', 'full')
            analysis.setdefault('issues', [])
            analysis.setdefault('warnings', [])
            analysis.setdefault('recommendations', [])
            analysis.setdefault('confidence', 0.5)
            
            return {
                'success': True,
                'method': 'ai_analysis',
                **analysis
            }
        except Exception as e:
            logger.error(f"Error parsing AI analysis: {e}")
            return {
                'success': False,
                'method': 'ai_analysis',
                'error': str(e)
            }
    
    def _basic_analysis(self, status: Dict, validation: Dict) -> Dict:
        """Basic analysis without AI"""
        should_train = validation.get('ready_for_training', False)
        issues = validation.get('issues', [])
        warnings = validation.get('warnings', [])
        
        recommendations = []
        if should_train:
            recommendations.append("Proceed with training")
        elif issues:
            recommendations.append(f"Fix {len(issues)} critical issues first")
        elif warnings:
            recommendations.append(f"Address {len(warnings)} warnings")
        else:
            recommendations.append("Collect more data before training")
        
        return {
            'success': True,
            'method': 'basic_analysis',
            'should_train': should_train,
            'reason': 'Based on validation status',
            'strategy': 'full',
            'strategy_reason': 'Default strategy',
            'issues': issues,
            'warnings': warnings,
            'recommendations': recommendations,
            'confidence': 0.7 if should_train else 0.5
        }
    
    def execute_training_plan(self, plan: Dict) -> Dict:
        """
        Execute a training plan recommended by the agent
        
        Args:
            plan: Training plan from analyze_situation()
            
        Returns:
            Training execution results
        """
        try:
            if not plan.get('should_train', False):
                return {
                    'success': False,
                    'reason': plan.get('reason', 'Training not recommended'),
                    'skipped': True
                }
            
            strategy = plan.get('strategy', 'full')
            
            logger.info(f"🤖 AI Agent executing {strategy} training strategy...")
            logger.info(f"   Reason: {plan.get('reason', 'No reason provided')}")
            
            # Execute based on strategy
            if strategy == 'full':
                result = self.auto_training_service.trigger_auto_training(force=True)
            elif strategy == 'incremental':
                result = self.llm_trainer.analyze_and_train_from_texts(limit=None, reprocess=False)
            else:  # minimal
                result = self.llm_trainer.analyze_and_train_from_texts(limit=10, reprocess=False)
            
            return {
                'success': result.get('success', False),
                'strategy': strategy,
                'result': result,
                'plan_executed': True
            }
            
        except Exception as e:
            logger.error(f"Error executing training plan: {e}")
            return {
                'success': False,
                'error': str(e),
                'plan_executed': False
            }
    
    def run_full_cycle(self) -> Dict:
        """
        Run a full training cycle: analyze → decide → execute → report
        
        Returns:
            Complete cycle results
        """
        logger.info("🤖 Training Agent - Starting full cycle...")
        
        # Step 1: Analyze situation
        logger.info("📊 Step 1: Analyzing training situation...")
        analysis = self.analyze_situation()
        
        if not analysis.get('success'):
            return {
                'success': False,
                'stage': 'analysis',
                'error': analysis.get('error', 'Analysis failed'),
                'analysis': analysis
            }
        
        # Log analysis results
        logger.info(f"✅ Analysis complete:")
        logger.info(f"   Should train: {analysis.get('should_train', False)}")
        logger.info(f"   Reason: {analysis.get('reason', 'No reason')}")
        logger.info(f"   Strategy: {analysis.get('strategy', 'full')}")
        logger.info(f"   Confidence: {analysis.get('confidence', 0):.2f}")
        
        if analysis.get('issues'):
            logger.warning(f"   ⚠️  {len(analysis['issues'])} issues found")
        if analysis.get('warnings'):
            logger.warning(f"   ⚠️  {len(analysis['warnings'])} warnings found")
        
        # Step 2: Execute plan
        if analysis.get('should_train', False):
            logger.info("🚀 Step 2: Executing training plan...")
            execution = self.execute_training_plan(analysis)
            
            return {
                'success': execution.get('success', False),
                'stage': 'execution',
                'analysis': analysis,
                'execution': execution,
                'recommendations': analysis.get('recommendations', [])
            }
        else:
            logger.info("⏸️  Step 2: Training not recommended - skipping")
            return {
                'success': True,
                'stage': 'skipped',
                'reason': analysis.get('reason', 'Training not needed'),
                'analysis': analysis,
                'execution': None,
                'recommendations': analysis.get('recommendations', [])
            }
    
    def get_agent_status(self) -> Dict:
        """
        Get current agent status and capabilities
        
        Returns:
            Agent status information
        """
        status = self.status_service.get_comprehensive_status()
        validation = self.validator.validate_all_requirements()
        
        # Check AI availability
        ai_enabled = hasattr(self, 'client') and self.client is not None
        
        return {
            'agent_active': True,
            'ai_enabled': ai_enabled,
            'system_status': status,
            'validation_status': validation,
            'capabilities': {
                'can_analyze': True,
                'can_train': True,
                'can_validate': True,
                'can_reason': ai_enabled
            }
        }

