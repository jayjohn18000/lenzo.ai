# backend/judge/steps/consensus_enhanced.py
"""
Enhanced consensus algorithm with weighted scoring and confidence intervals
"""

import numpy as np
import logging
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from backend.judge.schemas import Candidate

logger = logging.getLogger(__name__)

@dataclass
class ConsensusMetrics:
    """Detailed consensus metrics"""
    winner_idx: int
    winner_score: float
    confidence: float
    agreement_score: float
    score_variance: float
    margin_of_victory: float


class EnhancedConsensus:
    """Enhanced consensus with model weighting and statistical analysis"""
    
    def __init__(self):
        # Model reliability weights based on historical performance
        self.model_weights = {
            "openai/gpt-4o": 1.2,
            "openai/gpt-4o-mini": 1.1,
            "anthropic/claude-3.5-sonnet": 1.2,
            "anthropic/claude-3-opus": 1.15,
            "anthropic/claude-3-sonnet": 1.05,
            "anthropic/claude-3-haiku": 0.95,
            "google/gemini-pro-1.5": 1.0,
            "google/gemini-flash-1.5": 0.9,
            "meta-llama/llama-3.1-70b": 0.95,
            "mistralai/mistral-large": 1.0,
            "openai/gpt-3.5-turbo": 0.85
        }
        
        # Trait importance weights
        self.trait_weights = {
            "accuracy": 1.5,
            "relevance": 1.3,
            "completeness": 1.0,
            "clarity": 0.9,
            "coherence": 1.1,
            "non_hallucinated": 1.4,
            "citations": 1.2
        }
    
    def calculate_consensus(
        self,
        judge_scores: Dict[int, Dict[str, float]],
        candidates: List[Candidate],
        rubric: Optional[Dict[str, float]] = None
    ) -> ConsensusMetrics:
        """Calculate weighted consensus with confidence metrics"""
        
        if not judge_scores:
            return ConsensusMetrics(-1, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Calculate weighted scores for each candidate
        weighted_scores = {}
        score_details = {}
        
        for idx, trait_scores in judge_scores.items():
            if idx >= len(candidates):
                continue
            
            candidate = candidates[idx]
            model_weight = self._get_model_weight(candidate.model)
            
            # Calculate weighted trait scores
            weighted_trait_scores = self._weight_trait_scores(trait_scores, rubric)
            
            # Calculate final weighted score
            final_score = np.mean(list(weighted_trait_scores.values())) * model_weight
            
            weighted_scores[idx] = final_score
            score_details[idx] = {
                'raw_score': np.mean(list(trait_scores.values())),
                'weighted_score': final_score,
                'model_weight': model_weight,
                'trait_breakdown': weighted_trait_scores
            }
        
        # Find winner
        winner_idx = max(weighted_scores, key=weighted_scores.get)
        winner_score = weighted_scores[winner_idx]
        
        # Calculate confidence metrics
        confidence = self._calculate_confidence(weighted_scores, score_details)
        agreement = self._calculate_agreement(judge_scores)
        variance = self._calculate_variance(weighted_scores)
        margin = self._calculate_margin(weighted_scores, winner_idx)
        
        # Log detailed analysis
        self._log_analysis(candidates, score_details, winner_idx, confidence)
        
        return ConsensusMetrics(
            winner_idx=winner_idx,
            winner_score=winner_score,
            confidence=confidence,
            agreement_score=agreement,
            score_variance=variance,
            margin_of_victory=margin
        )
    
    def _get_model_weight(self, model_name: str) -> float:
        """Get reliability weight for model"""
        # Check exact match first
        if model_name in self.model_weights:
            return self.model_weights[model_name]
        
        # Check partial matches
        model_lower = model_name.lower()
        for pattern, weight in self.model_weights.items():
            if pattern.lower() in model_lower:
                return weight
        
        # Default weight for unknown models
        return 0.9
    
    def _weight_trait_scores(
        self, 
        trait_scores: Dict[str, float],
        rubric: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """Apply importance weights to trait scores"""
        weighted = {}
        
        for trait, score in trait_scores.items():
            # Get trait weight from rubric or defaults
            if rubric and trait in rubric:
                trait_weight = rubric[trait]
            else:
                trait_weight = self.trait_weights.get(trait, 1.0)
            
            weighted[trait] = score * trait_weight
        
        return weighted
    
    def _calculate_confidence(
        self,
        weighted_scores: Dict[int, float],
        score_details: Dict[int, Dict]
    ) -> float:
        """Calculate overall confidence in the selection"""
        
        if len(weighted_scores) < 2:
            return 0.9  # High confidence with single candidate
        
        scores = list(weighted_scores.values())
        
        # Factor 1: Score separation (how much better is winner)
        sorted_scores = sorted(scores, reverse=True)
        separation = (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0] if sorted_scores[0] > 0 else 0
        
        # Factor 2: Agreement among top candidates
        top_scores = sorted_scores[:3] if len(sorted_scores) >= 3 else sorted_scores
        agreement = 1 - np.std(top_scores) if len(top_scores) > 1 else 1.0
        
        # Factor 3: Winner's absolute score
        winner_absolute = sorted_scores[0]
        
        # Combine factors
        confidence = (
            0.4 * separation +      # How much winner stands out
            0.3 * agreement +       # How much top candidates agree
            0.3 * winner_absolute   # How good the winner is absolutely
        )
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_agreement(self, judge_scores: Dict[int, Dict[str, float]]) -> float:
        """Calculate inter-trait agreement score"""
        
        all_variances = []
        
        # Calculate variance for each trait across candidates
        traits = set()
        for scores in judge_scores.values():
            traits.update(scores.keys())
        
        for trait in traits:
            trait_scores = []
            for scores in judge_scores.values():
                if trait in scores:
                    trait_scores.append(scores[trait])
            
            if len(trait_scores) > 1:
                variance = np.var(trait_scores)
                all_variances.append(variance)
        
        # Low variance = high agreement
        if all_variances:
            avg_variance = np.mean(all_variances)
            agreement = 1 - min(avg_variance, 1.0)
            return agreement
        
        return 0.5
    
    def _calculate_variance(self, weighted_scores: Dict[int, float]) -> float:
        """Calculate score variance across candidates"""
        if len(weighted_scores) <= 1:
            return 0.0
        
        scores = list(weighted_scores.values())
        return float(np.var(scores))
    
    def _calculate_margin(self, weighted_scores: Dict[int, float], winner_idx: int) -> float:
        """Calculate margin of victory"""
        if len(weighted_scores) <= 1:
            return 1.0
        
        winner_score = weighted_scores[winner_idx]
        other_scores = [s for i, s in weighted_scores.items() if i != winner_idx]
        
        if not other_scores:
            return 1.0
        
        second_best = max(other_scores)
        margin = (winner_score - second_best) / winner_score if winner_score > 0 else 0
        
        return margin
    
    def _log_analysis(
        self,
        candidates: List[Candidate],
        score_details: Dict,
        winner_idx: int,
        confidence: float
    ):
        """Log detailed consensus analysis"""
        logger.info("=== Consensus Analysis ===")
        logger.info(f"Winner: Model {candidates[winner_idx].model} (idx: {winner_idx})")
        logger.info(f"Confidence: {confidence:.3f}")
        
        # Log top 3 candidates
        sorted_details = sorted(
            score_details.items(),
            key=lambda x: x[1]['weighted_score'],
            reverse=True
        )
        
        for i, (idx, details) in enumerate(sorted_details[:3]):
            model = candidates[idx].model if idx < len(candidates) else "unknown"
            logger.info(
                f"  #{i+1}: {model} - "
                f"Raw: {details['raw_score']:.3f}, "
                f"Weighted: {details['weighted_score']:.3f}, "
                f"Model Weight: {details['model_weight']:.2f}"
            )


def ensemble_consensus_enhanced(
    judge_scores: Dict[int, Dict[str, float]],
    candidates: List[Candidate],
    rubric: Optional[Dict[str, float]] = None
) -> Tuple[int, float, Dict[str, float]]:
    """
    Enhanced consensus function with backward compatibility
    
    Returns: (winner_idx, confidence, metrics_dict)
    """
    consensus = EnhancedConsensus()
    metrics = consensus.calculate_consensus(judge_scores, candidates, rubric)
    
    # Return in compatible format with additional metrics
    metrics_dict = {
        'winner_score': metrics.winner_score,
        'confidence': metrics.confidence,
        'agreement': metrics.agreement_score,
        'variance': metrics.score_variance,
        'margin': metrics.margin_of_victory
    }
    
    return metrics.winner_idx, metrics.confidence, metrics_dict


# Fallback to simple consensus if needed
def simple_consensus_fallback(
    judge_scores: Dict[int, Dict[str, float]]
) -> Tuple[int, float]:
    """Simple averaging fallback"""
    if not judge_scores:
        return -1, 0.0
    
    best_idx, best_avg = -1, -1.0
    
    for idx, trait_scores in judge_scores.items():
        if trait_scores:
            avg = sum(trait_scores.values()) / len(trait_scores)
            if avg > best_avg:
                best_idx, best_avg = idx, avg
    
    return best_idx, best_avg