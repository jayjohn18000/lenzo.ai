# backend/judge/steps/enhanced_scoring.py
"""
Enhanced scoring engine with confidence weighting, hallucination detection,
and model reliability scoring for NextAGI truth routing.
"""

import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from backend.judge.schemas import Candidate
from backend.middleware.validation import ScoringValidator

@dataclass
class TrustMetrics:
    """Comprehensive trust metrics for model responses"""
    reliability_score: float  # Based on model track record
    consistency_score: float  # Cross-model agreement
    hallucination_risk: float  # Likelihood of fabricated info
    citation_quality: float   # Quality of sources/references
    confidence_score: float   # Overall confidence (0-1)

class EnhancedScorer:
    """
    Advanced scoring engine that combines multiple signals:
    - Model reliability based on benchmarks
    - Hallucination pattern detection
    - Cross-model consensus analysis
    - Citation and factual grounding
    """
    
    def __init__(self):
        # Model reliability scores based on evaluation benchmarks
        self.model_reliability = {
            "openai/gpt-4": 0.95,
            "openai/gpt-4-turbo": 0.94,
            "anthropic/claude-3-opus": 0.93,
            "anthropic/claude-3.5-sonnet": 0.92,
            "anthropic/claude-3-sonnet": 0.90,
            "google/gemini-pro": 0.87,
            "mistral/mistral-large": 0.85,
            "meta/llama-3-70b-instruct": 0.82,
            "mistral/mistral-7b-instruct": 0.78,
            "meta/llama-3-8b-instruct": 0.75,
            "openai/gpt-3.5-turbo": 0.80,
        }
        
        # Hallucination indicator patterns
        self.hallucination_patterns = [
            r"according to (?:recent )?studies",
            r"experts (?:believe|say|claim)",
            r"it is (?:widely )?known",
            r"research (?:shows|indicates|suggests)",
            r"scientists have (?:found|discovered)",
            r"data shows",
            r"statistics reveal",
            r"as reported by",
            r"sources confirm",
            r"documentation states"
        ]
        
        # Authority claim patterns (often hallucinated)
        self.vague_authority_patterns = [
            r"many experts",
            r"most scientists",
            r"leading researchers",
            r"top universities",
            r"major studies",
            r"recent findings"
        ]
        
        # Citation quality indicators
        self.citation_indicators = [
            r"https?://[^\s]+",  # URLs
            r"\b\d{4}\b",        # Years
            r"et al\.",          # Academic citations
            r"DOI:",             # Digital Object Identifiers
            r"PMID:",            # PubMed IDs
            r"arXiv:",           # ArXiv papers
        ]

    def calculate_trust_metrics(self, 
                              candidate: Candidate, 
                              judge_scores: Dict[str, float],
                              all_candidates: List[Candidate]) -> TrustMetrics:
        """Calculate comprehensive trust metrics for a candidate response"""
        
        # 1. Base model reliability
        reliability_score = self.model_reliability.get(candidate.model, 0.7)
        
        # 2. Judge scoring average
        judge_avg = np.mean(list(judge_scores.values())) if judge_scores else 0.5
        
        # 3. Hallucination risk assessment
        hallucination_risk = self._assess_hallucination_risk(candidate.text)
        
        # 4. Citation quality
        citation_quality = self._assess_citation_quality(candidate.text)
        
        # 5. Cross-model consistency
        consistency_score = self._calculate_consistency(candidate, all_candidates)
        
        # 6. Overall confidence calculation
        confidence_score = self._calculate_overall_confidence(
            reliability_score, judge_avg, hallucination_risk, 
            citation_quality, consistency_score
        )
        
        return TrustMetrics(
            reliability_score=reliability_score,
            consistency_score=consistency_score,
            hallucination_risk=hallucination_risk,
            citation_quality=citation_quality,
            confidence_score=confidence_score
        )

    def calculate_trust_metrics_validated(self, candidate, judge_scores, all_candidates):
        """Calculate trust metrics with validation"""
        # Get raw metrics
        metrics = self.calculate_trust_metrics(candidate, judge_scores, all_candidates)
        
        # Validate all confidence/score fields
        return TrustMetrics(
            reliability_score=ScoringValidator.validate_confidence(metrics.reliability_score),
            consistency_score=ScoringValidator.validate_confidence(metrics.consistency_score),
            hallucination_risk=ScoringValidator.validate_confidence(metrics.hallucination_risk),
            citation_quality=ScoringValidator.validate_confidence(metrics.citation_quality),
            confidence_score=ScoringValidator.validate_confidence(metrics.confidence_score)
        )

    def _assess_hallucination_risk(self, text: str) -> float:
        """
        Assess risk of hallucination based on linguistic patterns.
        Returns 0.0 (low risk) to 1.0 (high risk)
        """
        if not text:
            return 1.0
            
        text_lower = text.lower()
        
        # Count hallucination indicator patterns
        hallucination_flags = 0
        for pattern in self.hallucination_patterns:
            hallucination_flags += len(re.findall(pattern, text_lower))
        
        # Count vague authority claims
        vague_authority_flags = 0
        for pattern in self.vague_authority_patterns:
            vague_authority_flags += len(re.findall(pattern, text_lower))
        
        # Calculate risk score
        text_length = len(text.split())
        if text_length == 0:
            return 1.0
            
        # Normalize by text length (flags per 100 words)
        normalized_hallucination = (hallucination_flags / max(text_length, 1)) * 100
        normalized_authority = (vague_authority_flags / max(text_length, 1)) * 100
        
        # Risk calculation
        risk_score = min(1.0, (normalized_hallucination * 0.7) + (normalized_authority * 0.3))
        
        return risk_score

    def _assess_citation_quality(self, text: str) -> float:
        """
        Assess quality of citations and references.
        Returns 0.0 (no citations) to 1.0 (high-quality citations)
        """
        if not text:
            return 0.0
        
        citation_count = 0
        for pattern in self.citation_indicators:
            citation_count += len(re.findall(pattern, text))
        
        # Quality scoring
        if citation_count == 0:
            return 0.0
        elif citation_count <= 2:
            return 0.4
        elif citation_count <= 5:
            return 0.7
        else:
            return 1.0

    def _calculate_consistency(self, 
                             target_candidate: Candidate, 
                             all_candidates: List[Candidate]) -> float:
        """
        Calculate how consistent this candidate is with other model outputs.
        Uses simple semantic similarity approximation.
        """
        if len(all_candidates) <= 1:
            return 0.5  # Default when no comparison possible
        
        target_text = target_candidate.text.lower()
        target_words = set(target_text.split())
        
        similarities = []
        for candidate in all_candidates:
            if candidate.model == target_candidate.model:
                continue
                
            other_text = candidate.text.lower()
            other_words = set(other_text.split())
            
            # Jaccard similarity
            intersection = len(target_words & other_words)
            union = len(target_words | other_words)
            
            if union == 0:
                similarity = 0.0
            else:
                similarity = intersection / union
                
            similarities.append(similarity)
        
        return np.mean(similarities) if similarities else 0.5

    def _calculate_overall_confidence(self, 
                                    reliability: float,
                                    judge_score: float, 
                                    hallucination_risk: float,
                                    citation_quality: float,
                                    consistency: float) -> float:
        """
        Calculate overall confidence score using weighted combination.
        """
        # Invert hallucination risk (lower risk = higher confidence)
        hallucination_confidence = 1.0 - hallucination_risk
        
        # Weighted combination
        confidence = (
            0.25 * reliability +           # Model track record
            0.30 * judge_score +          # LLM judge evaluation
            0.20 * hallucination_confidence +  # Hallucination safety
            0.15 * citation_quality +     # Source grounding
            0.10 * consistency            # Cross-model agreement
        )
        
        return max(0.0, min(1.0, confidence))

    def rank_candidates_by_trust(self, 
                                candidates: List[Candidate],
                                judge_scores: Dict[int, Dict[str, float]]) -> List[Tuple[int, TrustMetrics]]:
        """
        Rank all candidates by comprehensive trust metrics.
        Returns list of (candidate_index, trust_metrics) tuples, sorted by confidence.
        """
        rankings = []
        
        for i, candidate in enumerate(candidates):
            candidate_judge_scores = judge_scores.get(i, {})
            trust_metrics = self.calculate_trust_metrics(
                candidate, candidate_judge_scores, candidates
            )
            rankings.append((i, trust_metrics))
        
        # Sort by confidence score (highest first)
        rankings.sort(key=lambda x: x[1].confidence_score, reverse=True)
        
        return rankings

    def explain_selection(self, winner_metrics: TrustMetrics, winner_candidate: Candidate) -> str:
        """Generate human-readable explanation for why this answer was selected"""
        explanation_parts = []
        
        # Model reliability
        reliability = winner_metrics.reliability_score
        if reliability >= 0.9:
            explanation_parts.append(f"High-reliability model ({winner_candidate.model})")
        elif reliability >= 0.8:
            explanation_parts.append(f"Reliable model ({winner_candidate.model})")
        
        # Confidence level
        confidence = winner_metrics.confidence_score
        if confidence >= 0.9:
            explanation_parts.append("very high confidence")
        elif confidence >= 0.8:
            explanation_parts.append("high confidence")
        elif confidence >= 0.7:
            explanation_parts.append("good confidence")
        else:
            explanation_parts.append("moderate confidence")
        
        # Hallucination assessment
        if winner_metrics.hallucination_risk < 0.2:
            explanation_parts.append("low hallucination risk")
        elif winner_metrics.hallucination_risk < 0.5:
            explanation_parts.append("moderate hallucination risk")
        
        # Citations
        if winner_metrics.citation_quality > 0.7:
            explanation_parts.append("well-cited")
        elif winner_metrics.citation_quality > 0.4:
            explanation_parts.append("some citations")
        
        return f"Selected for: {', '.join(explanation_parts)}"

# Usage example integration
async def enhanced_consensus_selection(candidates: List[Candidate], 
                                     judge_scores: Dict[int, Dict[str, float]]) -> Tuple[Candidate, Dict, float, str]:
    """
    Enhanced consensus selection using trust metrics.
    Returns: (winner_candidate, trust_metrics_dict, confidence, explanation)
    """
    scorer = EnhancedScorer()
    
    # Rank candidates by comprehensive trust metrics
    rankings = scorer.rank_candidates_by_trust(candidates, judge_scores)
    
    if not rankings:
        # Fallback to first candidate
        return candidates[0], {}, 0.5, "No valid candidates found"
    
    # Get winner (highest confidence)
    winner_idx, winner_metrics = rankings[0]
    winner_candidate = candidates[winner_idx]
    
    # Prepare metrics for API response
    metrics_dict = {
        "reliability_score": winner_metrics.reliability_score,
        "consistency_score": winner_metrics.consistency_score,
        "hallucination_risk": winner_metrics.hallucination_risk,
        "citation_quality": winner_metrics.citation_quality,
        "confidence_score": winner_metrics.confidence_score
    }
    
    # Generate explanation
    explanation = scorer.explain_selection(winner_metrics, winner_candidate)
    
    return winner_candidate, metrics_dict, winner_metrics.confidence_score, explanation