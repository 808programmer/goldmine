import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from django.utils import timezone

logger = logging.getLogger(__name__)

@dataclass
class TextQualityMetrics:
    """Metrics for text quality assessment"""
    readability_score: float  # 0-1, higher is better
    completeness_score: float  # 0-1, higher is better
    geological_content_score: float  # 0-1, higher is better
    encoding_issues: List[str]
    ocr_artifacts: List[str]
    suggested_actions: List[str]
    overall_score: float  # 0-1, weighted average

class DataQualityProcessor:
    """
    Process and improve the quality of extracted text from PDFs
    """
    
    def __init__(self):
        # Geological keywords for content scoring
        self.geological_keywords = [
            'geological', 'geology', 'formation', 'mineral', 'gold', 'copper', 'iron',
            'quartz', 'pyrite', 'arsenopyrite', 'vein', 'lode', 'deposit', 'ore',
            'greenstone', 'granite', 'sedimentary', 'metamorphic', 'alluvial',
            'latitude', 'longitude', 'elevation', 'coordinates', 'survey',
            'soil', 'rock', 'strata', 'bedrock', 'outcrop', 'fault', 'fold'
        ]
        
        # Common OCR artifacts and noise patterns
        self.ocr_artifacts = [
            r'[Łł]',  # Common OCR error for 'L'
            r'[Øø]',  # Common OCR error for 'O'
            r'[Ææ]',  # Common OCR error for 'AE'
            r'[Œœ]',  # Common OCR error for 'OE'
            r'[^\x00-\x7F\n\r\t.,;:!?\-_/\\()\[\]{}\'\" ]+',  # Non-ASCII chars
            r'\b[A-Z]{1,2}\d{1,2}\b',  # Likely OCR artifacts (e.g., "A1", "B2")
            r'\b\d{1,2}[A-Z]{1,2}\b',  # Likely OCR artifacts (e.g., "1A", "2B")
        ]
    
    def process_text_quality(self, text: str, filename: str = "") -> Tuple[str, TextQualityMetrics]:
        """
        Process text and return cleaned text with quality metrics
        
        Args:
            text: Raw extracted text
            filename: Original filename for logging
            
        Returns:
            Tuple of (cleaned_text, quality_metrics)
        """
        logger.info(f"Processing text quality for {filename}")
        
        # Step 1: Detect and fix encoding issues
        cleaned_text, encoding_issues = self._fix_encoding_issues(text)
        
        # Step 2: Remove OCR artifacts
        cleaned_text, ocr_artifacts = self._remove_ocr_artifacts(cleaned_text)
        
        # Step 3: Normalize formatting
        cleaned_text = self._normalize_formatting(cleaned_text)
        
        # Step 4: Calculate quality metrics
        metrics = self._calculate_quality_metrics(cleaned_text, encoding_issues, ocr_artifacts)
        
        # Step 5: Generate suggested actions
        metrics.suggested_actions = self._generate_suggested_actions(metrics)
        
        logger.info(f"Text quality processing complete for {filename}. Overall score: {metrics.overall_score:.2f}")
        
        return cleaned_text, metrics
    
    def _fix_encoding_issues(self, text: str) -> Tuple[str, List[str]]:
        """
        Detect and fix common encoding issues
        
        Args:
            text: Raw text
            
        Returns:
            Tuple of (fixed_text, list_of_issues_found)
        """
        issues = []
        fixed_text = text
        
        # Common encoding fixes
        encoding_fixes = {
            'Ł': 'L', 'ł': 'l',  # Polish L
            'Ø': 'O', 'ø': 'o',  # Danish O
            'Æ': 'AE', 'æ': 'ae',  # Danish AE
            'Œ': 'OE', 'œ': 'oe',  # French OE
            'Ñ': 'N', 'ñ': 'n',  # Spanish N
            'Ç': 'C', 'ç': 'c',  # French C
        }
        
        for bad_char, good_char in encoding_fixes.items():
            if bad_char in fixed_text:
                fixed_text = fixed_text.replace(bad_char, good_char)
                issues.append(f"Fixed encoding: '{bad_char}' -> '{good_char}'")
        
        # Remove other non-ASCII characters (except basic punctuation)
        original_length = len(fixed_text)
        fixed_text = re.sub(r'[^\x00-\x7F\n\r\t.,;:!?\-_/\\()\[\]{}\'\" ]+', '', fixed_text)
        if len(fixed_text) < original_length:
            issues.append(f"Removed {original_length - len(fixed_text)} non-ASCII characters")
        
        return fixed_text, issues
    
    def _remove_ocr_artifacts(self, text: str) -> Tuple[str, List[str]]:
        """
        Remove common OCR artifacts and noise
        
        Args:
            text: Text to clean
            
        Returns:
            Tuple of (cleaned_text, list_of_artifacts_removed)
        """
        artifacts = []
        cleaned_text = text
        
        # Remove common OCR artifacts
        for pattern in self.ocr_artifacts:
            matches = re.findall(pattern, cleaned_text)
            if matches:
                cleaned_text = re.sub(pattern, '', cleaned_text)
                artifacts.append(f"Removed {len(matches)} OCR artifacts matching pattern: {pattern}")
        
        # Remove excessive whitespace
        original_length = len(cleaned_text)
        cleaned_text = re.sub(r'[ ]{2,}', ' ', cleaned_text)  # Multiple spaces
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)  # Multiple newlines
        if len(cleaned_text) < original_length:
            artifacts.append("Normalized excessive whitespace")
        
        return cleaned_text, artifacts
    
    def _normalize_formatting(self, text: str) -> str:
        """
        Normalize text formatting for consistency
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _calculate_quality_metrics(self, text: str, encoding_issues: List[str], 
                                 ocr_artifacts: List[str]) -> TextQualityMetrics:
        """
        Calculate quality metrics for the text
        
        Args:
            text: Cleaned text
            encoding_issues: List of encoding issues found
            ocr_artifacts: List of OCR artifacts removed
            
        Returns:
            TextQualityMetrics object
        """
        # Readability score (based on sentence structure and word length)
        readability_score = self._calculate_readability_score(text)
        
        # Completeness score (based on text length and structure)
        completeness_score = self._calculate_completeness_score(text)
        
        # Geological content score (based on presence of geological keywords)
        geological_content_score = self._calculate_geological_content_score(text)
        
        # Overall score (weighted average)
        overall_score = (
            readability_score * 0.3 +
            completeness_score * 0.3 +
            geological_content_score * 0.4
        )
        
        return TextQualityMetrics(
            readability_score=readability_score,
            completeness_score=completeness_score,
            geological_content_score=geological_content_score,
            encoding_issues=encoding_issues,
            ocr_artifacts=ocr_artifacts,
            suggested_actions=[],
            overall_score=overall_score
        )
    
    def _calculate_readability_score(self, text: str) -> float:
        """Calculate readability score based on sentence structure"""
        if not text.strip():
            return 0.0
        
        # Count sentences (simple heuristic)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Calculate average sentence length
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Score based on sentence length (optimal range: 10-25 words)
        if 10 <= avg_sentence_length <= 25:
            return 1.0
        elif 5 <= avg_sentence_length <= 40:
            return 0.7
        else:
            return 0.3
    
    def _calculate_completeness_score(self, text: str) -> float:
        """Calculate completeness score based on text length and structure"""
        if not text.strip():
            return 0.0
        
        # Score based on text length
        word_count = len(text.split())
        
        if word_count >= 1000:
            return 1.0
        elif word_count >= 500:
            return 0.8
        elif word_count >= 200:
            return 0.6
        elif word_count >= 100:
            return 0.4
        else:
            return 0.2
    
    def _calculate_geological_content_score(self, text: str) -> float:
        """Calculate geological content score based on keyword presence"""
        if not text.strip():
            return 0.0
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.geological_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        # Score based on number of geological keywords found
        keyword_ratio = len(found_keywords) / len(self.geological_keywords)
        
        if keyword_ratio >= 0.3:
            return 1.0
        elif keyword_ratio >= 0.2:
            return 0.8
        elif keyword_ratio >= 0.1:
            return 0.6
        elif keyword_ratio >= 0.05:
            return 0.4
        else:
            return 0.1
    
    def _generate_suggested_actions(self, metrics: TextQualityMetrics) -> List[str]:
        """Generate suggested actions based on quality metrics"""
        actions = []
        
        if metrics.overall_score < 0.5:
            actions.append("Consider manual review of extracted text")
        
        if metrics.readability_score < 0.5:
            actions.append("Text may have OCR issues - consider re-extraction")
        
        if metrics.geological_content_score < 0.3:
            actions.append("Low geological content - may not be suitable for analysis")
        
        if len(metrics.encoding_issues) > 0:
            actions.append("Encoding issues detected - consider source file quality")
        
        if len(metrics.ocr_artifacts) > 0:
            actions.append("OCR artifacts detected - consider using different OCR method")
        
        if not actions:
            actions.append("Text quality is acceptable for analysis")
        
        return actions
    
    def should_flag_for_manual_review(self, metrics: TextQualityMetrics) -> bool:
        """Determine if text should be flagged for manual review"""
        return (
            metrics.overall_score < 0.5 or
            metrics.readability_score < 0.3 or
            metrics.geological_content_score < 0.2 or
            len(metrics.encoding_issues) > 5 or
            len(metrics.ocr_artifacts) > 10
        ) 