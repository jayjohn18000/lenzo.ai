# backend/judge/model_selector.py
"""
Smart Model Selection Engine for NextAGI
Optimizes model selection based on query type, cost, speed, and quality requirements.
"""

import re
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np


class QueryType(Enum):
    CODING = "coding"
    FACTUAL = "factual"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    MATHEMATICAL = "mathematical"
    CONVERSATIONAL = "conversational"
    TECHNICAL = "technical"
    RESEARCH = "research"


class SelectionMode(Enum):
    SPEED = "speed"
    QUALITY = "quality"
    BALANCED = "balanced"
    COST = "cost"


@dataclass
class ModelSpecs:
    """Model specifications and performance characteristics"""

    name: str
    cost_per_1k_tokens: float
    avg_response_time_ms: int
    quality_score: float  # 0-1, based on benchmarks
    strengths: List[QueryType]
    context_window: int
    supports_function_calling: bool = False
    supports_vision: bool = False


class SmartModelSelector:
    """
    Intelligent model selection engine that chooses optimal models
    based on query characteristics and user preferences.
    """

    def __init__(self):
        self.model_specs = self._initialize_model_specs()
        self.query_classifiers = self._initialize_classifiers()
        self.performance_history = {}  # Track real-world performance

    def _initialize_model_specs(self) -> Dict[str, ModelSpecs]:
        """Initialize model specifications based on current benchmarks"""
        return {
            "openai/gpt-4": ModelSpecs(
                name="openai/gpt-4",
                cost_per_1k_tokens=0.03,
                avg_response_time_ms=3500,
                quality_score=0.95,
                strengths=[
                    QueryType.CODING,
                    QueryType.ANALYTICAL,
                    QueryType.MATHEMATICAL,
                ],
                context_window=128000,
                supports_function_calling=True,
            ),
            "openai/gpt-4-turbo": ModelSpecs(
                name="openai/gpt-4-turbo",
                cost_per_1k_tokens=0.01,
                avg_response_time_ms=2800,
                quality_score=0.94,
                strengths=[QueryType.CODING, QueryType.ANALYTICAL, QueryType.RESEARCH],
                context_window=128000,
                supports_function_calling=True,
                supports_vision=True,
            ),
            "openai/gpt-4o-mini": ModelSpecs(
                name="openai/gpt-4o-mini",
                cost_per_1k_tokens=0.00015,
                avg_response_time_ms=1200,
                quality_score=0.85,
                strengths=[QueryType.CONVERSATIONAL, QueryType.FACTUAL],
                context_window=128000,
                supports_function_calling=True,
            ),
            "anthropic/claude-3-opus": ModelSpecs(
                name="anthropic/claude-3-opus",
                cost_per_1k_tokens=0.015,
                avg_response_time_ms=4000,
                quality_score=0.93,
                strengths=[
                    QueryType.CREATIVE,
                    QueryType.ANALYTICAL,
                    QueryType.RESEARCH,
                ],
                context_window=200000,
            ),
            "anthropic/claude-3.5-sonnet": ModelSpecs(
                name="anthropic/claude-3.5-sonnet",
                cost_per_1k_tokens=0.003,
                avg_response_time_ms=2200,
                quality_score=0.92,
                strengths=[QueryType.CODING, QueryType.TECHNICAL, QueryType.ANALYTICAL],
                context_window=200000,
            ),
            "anthropic/claude-3-haiku": ModelSpecs(
                name="anthropic/claude-3-haiku",
                cost_per_1k_tokens=0.00025,
                avg_response_time_ms=1000,
                quality_score=0.82,
                strengths=[QueryType.CONVERSATIONAL, QueryType.FACTUAL],
                context_window=200000,
            ),
            "google/gemini-pro": ModelSpecs(
                name="google/gemini-pro",
                cost_per_1k_tokens=0.0005,
                avg_response_time_ms=2500,
                quality_score=0.87,
                strengths=[
                    QueryType.FACTUAL,
                    QueryType.RESEARCH,
                    QueryType.MATHEMATICAL,
                ],
                context_window=32000,
                supports_vision=True,
            ),
            "mistral/mistral-large": ModelSpecs(
                name="mistral/mistral-large",
                cost_per_1k_tokens=0.008,
                avg_response_time_ms=2000,
                quality_score=0.85,
                strengths=[QueryType.CODING, QueryType.TECHNICAL],
                context_window=32000,
                supports_function_calling=True,
            ),
            "meta/llama-3-70b-instruct": ModelSpecs(
                name="meta/llama-3-70b-instruct",
                cost_per_1k_tokens=0.0009,
                avg_response_time_ms=3000,
                quality_score=0.82,
                strengths=[QueryType.CONVERSATIONAL, QueryType.CREATIVE],
                context_window=8000,
            ),
        }

    def _initialize_classifiers(self) -> Dict[QueryType, Dict]:
        """Initialize query classification patterns"""
        return {
            QueryType.CODING: {
                "keywords": [
                    "code",
                    "function",
                    "python",
                    "javascript",
                    "java",
                    "c++",
                    "algorithm",
                    "debug",
                    "programming",
                    "script",
                    "api",
                    "class",
                    "variable",
                    "loop",
                    "array",
                    "object",
                    "method",
                    "syntax",
                ],
                "patterns": [
                    r"write.*(?:code|function|script)",
                    r"(?:debug|fix).*(?:code|error|bug)",
                    r"implement.*(?:algorithm|function)",
                    r"create.*(?:class|api|endpoint)",
                    r"```\w+",  # Code blocks
                ],
            },
            QueryType.FACTUAL: {
                "keywords": [
                    "what is",
                    "when did",
                    "how many",
                    "who is",
                    "where is",
                    "define",
                    "definition",
                    "fact",
                    "information",
                    "data",
                    "statistics",
                    "history",
                    "biography",
                ],
                "patterns": [
                    r"^(?:what|when|where|who|how many|how much)",
                    r"(?:tell me about|information about)",
                    r"(?:define|definition of)",
                    r"(?:facts about|data on)",
                ],
            },
            QueryType.CREATIVE: {
                "keywords": [
                    "write",
                    "story",
                    "poem",
                    "creative",
                    "imagine",
                    "fiction",
                    "character",
                    "plot",
                    "narrative",
                    "script",
                    "dialogue",
                    "brainstorm",
                    "ideas",
                    "artistic",
                ],
                "patterns": [
                    r"write.*(?:story|poem|script|song)",
                    r"create.*(?:character|plot|narrative)",
                    r"imagine.*(?:scenario|world|situation)",
                    r"(?:brainstorm|generate).*ideas",
                ],
            },
            QueryType.ANALYTICAL: {
                "keywords": [
                    "analyze",
                    "compare",
                    "evaluate",
                    "assess",
                    "pros and cons",
                    "advantages",
                    "disadvantages",
                    "strengths",
                    "weaknesses",
                    "implications",
                    "consequences",
                    "impact",
                    "effectiveness",
                ],
                "patterns": [
                    r"(?:analyze|analyse).*(?:data|situation|problem)",
                    r"compare.*(?:and contrast|vs|versus)",
                    r"(?:evaluate|assess).*(?:performance|effectiveness)",
                    r"pros and cons",
                    r"advantages and disadvantages",
                ],
            },
            QueryType.MATHEMATICAL: {
                "keywords": [
                    "calculate",
                    "solve",
                    "equation",
                    "math",
                    "formula",
                    "derivative",
                    "integral",
                    "probability",
                    "statistics",
                    "algebra",
                    "geometry",
                    "calculus",
                    "optimization",
                ],
                "patterns": [
                    r"(?:solve|calculate).*(?:equation|problem)",
                    r"find.*(?:derivative|integral|solution)",
                    r"optimize.*(?:function|problem)",
                    r"\d+\s*[\+\-\*\/\^\=]\s*\d+",  # Math expressions
                    r"probability.*of",
                ],
            },
            QueryType.TECHNICAL: {
                "keywords": [
                    "technical",
                    "engineering",
                    "architecture",
                    "system",
                    "infrastructure",
                    "protocol",
                    "specification",
                    "documentation",
                    "implementation",
                    "deployment",
                    "configuration",
                    "optimization",
                ],
                "patterns": [
                    r"(?:technical|engineering).*(?:documentation|specification)",
                    r"(?:system|infrastructure).*(?:design|architecture)",
                    r"(?:implement|deploy).*(?:system|solution)",
                    r"(?:configure|optimize).*(?:performance|system)",
                ],
            },
            QueryType.RESEARCH: {
                "keywords": [
                    "research",
                    "study",
                    "investigate",
                    "explore",
                    "examine",
                    "literature review",
                    "paper",
                    "academic",
                    "scholarly",
                    "evidence",
                    "findings",
                    "methodology",
                    "hypothesis",
                ],
                "patterns": [
                    r"research.*(?:topic|subject|area)",
                    r"(?:literature review|systematic review)",
                    r"(?:investigate|explore).*(?:relationship|correlation)",
                    r"(?:academic|scholarly).*(?:paper|article|study)",
                ],
            },
            QueryType.CONVERSATIONAL: {
                "keywords": [
                    "hello",
                    "hi",
                    "thanks",
                    "please",
                    "help",
                    "advice",
                    "opinion",
                    "think",
                    "feel",
                    "chat",
                    "talk",
                    "discuss",
                ],
                "patterns": [
                    r"^(?:hi|hello|hey)",
                    r"(?:what do you think|your opinion)",
                    r"(?:can you help|please help)",
                    r"(?:let's talk|let's discuss)",
                ],
            },
        }

    def classify_query(self, prompt: str) -> Tuple[QueryType, float]:
        """
        Classify query type and return confidence score.
        Returns: (query_type, confidence_score)
        """
        prompt_lower = prompt.lower()
        scores = {}

        for query_type, classifier in self.query_classifiers.items():
            score = 0.0

            # Keyword matching
            keyword_matches = sum(
                1 for keyword in classifier["keywords"] if keyword in prompt_lower
            )
            keyword_score = min(1.0, keyword_matches / len(classifier["keywords"]) * 3)

            # Pattern matching
            pattern_matches = sum(
                1
                for pattern in classifier["patterns"]
                if re.search(pattern, prompt_lower, re.IGNORECASE)
            )
            pattern_score = min(1.0, pattern_matches / len(classifier["patterns"]) * 2)

            # Combined score
            scores[query_type] = (keyword_score * 0.6) + (pattern_score * 0.4)

        # Get best match
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]

        # Default to conversational if no clear match
        if confidence < 0.3:
            return QueryType.CONVERSATIONAL, 0.5

        return best_type, confidence

    def select_models(
        self,
        prompt: str,
        mode: SelectionMode = SelectionMode.BALANCED,
        max_models: int = 4,
        budget_per_request: Optional[float] = None,
    ) -> List[str]:
        """
        Select optimal models for the given prompt and constraints.

        Args:
            prompt: The user's query
            mode: Selection strategy (speed, quality, balanced, cost)
            max_models: Maximum number of models to select
            budget_per_request: Maximum cost budget for this request

        Returns:
            List of selected model names
        """
        # Classify the query
        query_type, confidence = self.classify_query(prompt)

        # Get candidate models
        candidates = list(self.model_specs.values())

        # Apply budget filter if specified
        if budget_per_request:
            estimated_tokens = min(len(prompt.split()) * 4, 2000)  # Rough estimate
            candidates = [
                model
                for model in candidates
                if model.cost_per_1k_tokens * (estimated_tokens / 1000)
                <= budget_per_request
            ]

        # Score models based on selection mode
        model_scores = []
        for model in candidates:
            score = self._calculate_model_score(model, query_type, mode, confidence)
            model_scores.append((model.name, score))

        # Sort by score and select top models
        model_scores.sort(key=lambda x: x[1], reverse=True)

        # Select diverse set of top models
        selected_models = self._select_diverse_models(
            model_scores[: max_models * 2], max_models, query_type
        )

        return selected_models

    def _calculate_model_score(
        self,
        model: ModelSpecs,
        query_type: QueryType,
        mode: SelectionMode,
        type_confidence: float,
    ) -> float:
        """Calculate overall score for a model given the query and mode"""

        # Base quality score
        quality_score = model.quality_score

        # Strength bonus for query type
        strength_bonus = 0.2 if query_type in model.strengths else 0.0

        # Mode-specific adjustments
        if mode == SelectionMode.SPEED:
            # Prioritize response time
            time_score = 1.0 - (
                model.avg_response_time_ms / 5000
            )  # Normalize to 5s max
            final_score = (
                (0.3 * quality_score) + (0.5 * time_score) + (0.2 * strength_bonus)
            )

        elif mode == SelectionMode.QUALITY:
            # Prioritize quality and strengths
            final_score = (0.7 * quality_score) + (0.3 * strength_bonus)

        elif mode == SelectionMode.COST:
            # Prioritize low cost
            cost_score = 1.0 - min(
                1.0, model.cost_per_1k_tokens / 0.03
            )  # Normalize to $0.03 max
            final_score = (
                (0.2 * quality_score) + (0.6 * cost_score) + (0.2 * strength_bonus)
            )

        else:  # BALANCED
            # Balanced consideration of all factors
            time_score = 1.0 - (model.avg_response_time_ms / 5000)
            cost_score = 1.0 - min(1.0, model.cost_per_1k_tokens / 0.03)
            final_score = (
                (0.4 * quality_score)
                + (0.2 * time_score)
                + (0.2 * cost_score)
                + (0.2 * strength_bonus)
            )

        # Apply confidence weighting
        final_score *= 0.7 + 0.3 * type_confidence

        # Add performance history bonus if available
        if model.name in self.performance_history:
            history_bonus = (
                self.performance_history[model.name].get("success_rate", 0.5) * 0.1
            )
            final_score += history_bonus

        return max(0.0, min(1.0, final_score))

    def _select_diverse_models(
        self,
        scored_models: List[Tuple[str, float]],
        max_models: int,
        query_type: QueryType,
    ) -> List[str]:
        """Select diverse set of models to avoid redundancy"""
        if not scored_models:
            return []

        selected = []
        model_families = set()

        for model_name, score in scored_models:
            if len(selected) >= max_models:
                break

            # Get model family (e.g., "openai", "anthropic")
            family = model_name.split("/")[0]

            # For first few selections, prioritize diversity
            if len(selected) < max_models // 2:
                if family not in model_families:
                    selected.append(model_name)
                    model_families.add(family)
            else:
                # Fill remaining slots with best scores
                selected.append(model_name)

        # Ensure we have at least one high-quality model
        if not selected:
            selected.append(scored_models[0][0])

        return selected

    def update_performance_history(
        self,
        model_name: str,
        success: bool,
        response_time: int,
        confidence_score: float,
    ):
        """Update model performance history for future selections"""
        if model_name not in self.performance_history:
            self.performance_history[model_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "avg_response_time": 0,
                "avg_confidence": 0,
                "success_rate": 0.5,
            }

        history = self.performance_history[model_name]
        history["total_requests"] += 1

        if success:
            history["successful_requests"] += 1

        # Update rolling averages
        n = history["total_requests"]
        history["avg_response_time"] = (
            history["avg_response_time"] * (n - 1) + response_time
        ) / n
        history["avg_confidence"] = (
            history["avg_confidence"] * (n - 1) + confidence_score
        ) / n
        history["success_rate"] = (
            history["successful_requests"] / history["total_requests"]
        )

    def get_model_recommendations(self, prompt: str) -> Dict:
        """Get detailed model recommendations with explanations"""
        query_type, confidence = self.classify_query(prompt)

        recommendations = {}
        for mode in SelectionMode:
            models = self.select_models(prompt, mode, max_models=3)
            recommendations[mode.value] = {
                "models": models,
                "explanation": self._explain_selection(models, query_type, mode),
            }

        return {
            "query_type": query_type.value,
            "type_confidence": confidence,
            "recommendations": recommendations,
        }

    def _explain_selection(
        self, models: List[str], query_type: QueryType, mode: SelectionMode
    ) -> str:
        """Generate explanation for model selection"""
        explanations = []

        if mode == SelectionMode.SPEED:
            explanations.append("Optimized for fast response times")
        elif mode == SelectionMode.QUALITY:
            explanations.append("Optimized for highest quality outputs")
        elif mode == SelectionMode.COST:
            explanations.append("Optimized for cost efficiency")
        else:
            explanations.append("Balanced optimization for speed, quality, and cost")

        if query_type != QueryType.CONVERSATIONAL:
            explanations.append(
                f"Selected models with strengths in {query_type.value} tasks"
            )

        return ". ".join(explanations)

    def estimate_request_cost(
        self,
        models: List[str],
        prompt_tokens: int,
        estimated_response_tokens: int = 500,
    ) -> Dict:
        """Estimate cost for running prompt across selected models"""
        total_cost = 0.0
        model_costs = {}

        for model_name in models:
            if model_name in self.model_specs:
                model = self.model_specs[model_name]
                total_tokens = prompt_tokens + estimated_response_tokens
                cost = (total_tokens / 1000) * model.cost_per_1k_tokens
                model_costs[model_name] = cost
                total_cost += cost

        return {
            "total_estimated_cost": round(total_cost, 4),
            "cost_per_model": model_costs,
            "estimated_tokens": prompt_tokens + estimated_response_tokens,
        }

    def get_fallback_models(self, failed_models: List[str]) -> List[str]:
        """Get fallback models when primary selections fail"""
        all_models = list(self.model_specs.keys())
        available_models = [m for m in all_models if m not in failed_models]

        if not available_models:
            return ["openai/gpt-4o-mini"]  # Ultimate fallback

        # Sort by reliability and cost
        fallback_scores = []
        for model_name in available_models:
            model = self.model_specs[model_name]
            # Score based on reliability and low cost
            score = (
                model.quality_score * 0.7
                + (1.0 - min(1.0, model.cost_per_1k_tokens / 0.01)) * 0.3
            )
            fallback_scores.append((model_name, score))

        fallback_scores.sort(key=lambda x: x[1], reverse=True)
        return [model[0] for model in fallback_scores[:2]]


# ADD THIS METHOD to your SmartModelSelector class
def get_model_specs_for_routes(self) -> Dict[str, Dict]:
    """
    Get model specifications formatted for the enhanced routes.py
    This ensures consistency between model_selector and routes.
    """
    return {
        name: {
            "cost_per_1k_tokens": spec.cost_per_1k_tokens,
            "avg_response_time_ms": spec.avg_response_time_ms,
            "quality_score": spec.quality_score,
            "strengths": [s.value for s in spec.strengths],
            "context_window": spec.context_window,
            "supports_function_calling": spec.supports_function_calling,
            "supports_vision": spec.supports_vision,
        }
        for name, spec in self.model_specs.items()
    }


# ADD THIS METHOD to your SmartModelSelector class
def calculate_response_confidence(
    self,
    candidate_text: str,
    model_name: str,
    response_time_ms: int,
    query_type: QueryType,
) -> float:
    """
    Calculate confidence score for a model response.
    Integrates with the enhanced routes confidence calculation.
    """
    base_confidence = 0.7

    # Text quality assessment
    text_length = len(candidate_text.split())
    if 20 <= text_length <= 200:
        base_confidence += 0.1
    elif text_length < 10:
        base_confidence -= 0.2

    # Response time factor based on model specs
    if model_name in self.model_specs:
        expected_time = self.model_specs[model_name].avg_response_time_ms
        time_ratio = response_time_ms / expected_time
        if 0.5 <= time_ratio <= 2.0:
            base_confidence += 0.05
        elif time_ratio > 3.0:
            base_confidence -= 0.1

    # Model strength alignment with query type
    if model_name in self.model_specs:
        model_strengths = self.model_specs[model_name].strengths
        if query_type in model_strengths:
            base_confidence += 0.1

    # Text quality heuristics
    text_lower = candidate_text.lower()
    if any(phrase in text_lower for phrase in ["i apologize", "i cannot", "unclear"]):
        base_confidence -= 0.1

    if any(
        phrase in text_lower
        for phrase in ["based on", "according to", "research shows"]
    ):
        base_confidence += 0.1

    # Performance history bonus
    if model_name in self.performance_history:
        history_bonus = (
            self.performance_history[model_name].get("avg_confidence", 0.5) * 0.1
        )
        base_confidence += history_bonus

    return max(0.0, min(1.0, base_confidence))


# ADD THIS METHOD to your SmartModelSelector class
def update_from_route_response(
    self, route_result: Dict, selected_models: List[str], response_time_ms: int
):
    """
    Update model performance history from route response data.
    Call this after each successful route execution.
    """
    winner_model = route_result.get("winner_model")
    confidence = route_result.get("confidence", 0.5)

    # Update performance for all attempted models
    for model in selected_models:
        success = model == winner_model
        self.update_performance_history(
            model_name=model,
            success=success,
            response_time=response_time_ms,
            confidence_score=confidence if success else confidence * 0.7,
        )


# ADD THIS METHOD to your SmartModelSelector class
def get_enhanced_model_details(
    self, candidates: List, judge_scores: Dict = None  # Candidate objects
) -> List[Dict]:
    """
    Generate enhanced model details for frontend display.
    Integrates candidate data with model specs and scoring.
    """
    model_details = []

    for i, candidate in enumerate(candidates):
        # Get query type for context
        query_type, _ = self.classify_query(
            candidate.text[:100]
        )  # Sample classification

        # Calculate confidence using integrated scoring
        confidence = self.calculate_response_confidence(
            candidate.text, candidate.model, candidate.gen_time_ms, query_type
        )

        # Apply judge scores if available
        if judge_scores and i in judge_scores:
            scores = judge_scores[i]
            if isinstance(scores, dict) and scores:
                judge_avg = sum(scores.values()) / len(scores)
                confidence = (confidence + judge_avg) / 2

        # Calculate cost
        cost = self.estimate_token_cost(
            candidate.model, candidate.tokens_in, candidate.tokens_out
        )

        model_details.append(
            {
                "model": candidate.model,
                "response": candidate.text,
                "confidence": confidence,
                "response_time_ms": candidate.gen_time_ms,
                "tokens_used": candidate.tokens_in + candidate.tokens_out,
                "cost": cost,
                "error": None,
                "performance_tier": getattr(candidate, "performance_tier", "medium"),
            }
        )

    return model_details


# ADD THIS METHOD to your SmartModelSelector class
def estimate_token_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
    """
    Estimate cost based on model specs and token usage.
    Uses actual model specifications from the selector.
    """
    if model in self.model_specs:
        cost_per_1k = self.model_specs[model].cost_per_1k_tokens
        total_tokens = tokens_in + tokens_out
        return (total_tokens / 1000) * cost_per_1k

    # Fallback cost estimation
    return (tokens_in + tokens_out) / 1000 * 0.002  # Conservative estimate


# ADD THIS METHOD to your SmartModelSelector class
def generate_selection_reasoning(
    self,
    candidates: List,
    winner_model: str,
    query_type: QueryType,
    selection_mode: SelectionMode,
) -> str:
    """
    Generate detailed reasoning for model selection decision.
    Provides transparency into the selection process.
    """
    total_models = len(candidates)
    avg_response_time = (
        sum(c.gen_time_ms for c in candidates) / total_models if candidates else 0
    )
    avg_confidence = (
        sum(
            self.calculate_response_confidence(
                c.text, c.model, c.gen_time_ms, query_type
            )
            for c in candidates
        )
        / total_models
        if candidates
        else 0
    )

    reasoning = f"""Model Selection Analysis:

• Query Type: {query_type.value.title()} (confidence-based classification)
• Selection Mode: {selection_mode.value.title()}
• Models Consulted: {total_models} simultaneously
• Winner: {winner_model.split('/')[-1] if '/' in winner_model else winner_model}

Performance Metrics:
• Average response time: {avg_response_time:.0f}ms
• Average confidence: {avg_confidence:.1%}
• Selection based on: {self._get_selection_criteria(selection_mode)}

Model Strengths Applied:
{self._explain_model_strengths(candidates, query_type)}

Winner selected based on optimal balance of quality, speed, cost, and domain expertise for this query type."""

    return reasoning


# ADD THIS HELPER METHOD to your SmartModelSelector class
def _get_selection_criteria(self, mode: SelectionMode) -> str:
    """Get human-readable selection criteria for the mode"""
    criteria = {
        SelectionMode.SPEED: "Response time optimization, maintaining quality threshold",
        SelectionMode.QUALITY: "Maximum output quality, domain expertise alignment",
        SelectionMode.BALANCED: "Optimal balance of speed, quality, and cost efficiency",
        SelectionMode.COST: "Cost optimization while maintaining acceptable quality",
    }
    return criteria.get(mode, "Balanced optimization")


# ADD THIS HELPER METHOD to your SmartModelSelector class
def _explain_model_strengths(self, candidates: List, query_type: QueryType) -> str:
    """Explain how model strengths align with query type"""
    explanations = []

    for candidate in candidates:
        if candidate.model in self.model_specs:
            model_spec = self.model_specs[candidate.model]
            model_name = candidate.model.split("/")[-1]

            if query_type in model_spec.strengths:
                explanations.append(
                    f"• {model_name}: Specialized in {query_type.value} tasks"
                )
            else:
                explanations.append(
                    f"• {model_name}: General-purpose model for comparison"
                )

    return (
        "\n".join(explanations)
        if explanations
        else "• All models provide general-purpose capabilities"
    )


# Integration helper functions
def select_models_for_request(
    prompt: str,
    mode: str = "balanced",
    max_models: int = 4,
    budget: Optional[float] = None,
) -> List[str]:
    """Main function to select models for a request"""
    selector = SmartModelSelector()
    selection_mode = SelectionMode(mode.lower())
    return selector.select_models(prompt, selection_mode, max_models, budget)


def get_query_analysis(prompt: str) -> Dict:
    """Analyze query and provide model recommendations"""
    selector = SmartModelSelector()
    return selector.get_model_recommendations(prompt)


def estimate_cost(models: List[str], prompt: str) -> Dict:
    """Estimate cost for running prompt across models"""
    selector = SmartModelSelector()
    prompt_tokens = len(prompt.split()) * 1.3  # Rough tokenization estimate
    return selector.estimate_request_cost(models, int(prompt_tokens))


def integrate_with_enhanced_routes(
    selector_instance: SmartModelSelector,
    candidates: List,
    judge_scores: Dict,
    query_type: QueryType,
    selection_mode: SelectionMode,
    winner_model: str,
) -> Dict[str, Any]:
    """
    Main integration function that ties model_selector with enhanced routes.
    Call this from your enhanced routes.py to get all the detailed data.
    """
    # Get enhanced model details
    model_details = selector_instance.get_enhanced_model_details(
        candidates, judge_scores
    )

    # Find winner confidence
    winner_confidence = 0.8  # Default
    for detail in model_details:
        if detail["model"] == winner_model:
            winner_confidence = detail["confidence"]
            break

    # Generate reasoning
    reasoning = selector_instance.generate_selection_reasoning(
        candidates, winner_model, query_type, selection_mode
    )

    # Calculate total cost
    total_cost = sum(detail["cost"] for detail in model_details)

    return {
        "model_details": model_details,
        "reasoning": reasoning,
        "total_cost": total_cost,
        "winner_confidence": winner_confidence,
    }
