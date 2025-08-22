# backend/judge/schemas.py
from typing import Any, Dict, List, Literal, Optional, TypedDict
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ---- Shared literals / types ----
PipelineID = Literal["judge", "tool_chain"]
ModelSelectionMode = Literal["balanced", "speed", "quality", "cost"]


# ---- Request models ----
class RouteOptions(BaseModel):
    """Optional knobs per request. Citations are kept on by default."""
    models: Optional[List[str]] = None                 # override fan-out models
    model_selection_mode: ModelSelectionMode = "balanced"  # NEW: smart model selection
    rubric: Optional[Dict[str, float]] = None          # trait -> weight (0..1)
    output_format: Literal["markdown", "json"] = "markdown"
    no_cache: bool = False
    require_citations: bool = True                     # we keep citations on for both pipelines
    max_parallel_requests: Optional[int] = None        # override MAX_PARALLEL_FANOUT


class RouteRequest(BaseModel):
    """Unified entry for routing + execution."""
    prompt: str
    pipeline_id: Optional[PipelineID] = None           # explicit override; else dispatcher decides
    category: Optional[str] = None                     # e.g., "Science", "Tech Support"
    expected_traits: Optional[List[str]] = None        # e.g., ["clarity","non-hallucinated"]
    options: RouteOptions = Field(default_factory=RouteOptions)


# ---- Internal execution / candidate models ----
class Candidate(BaseModel):
    text: str
    provider: str                                      # e.g., "openrouter"
    model: str                                         # e.g., "openai/gpt-4o-mini"
    tokens_in: int = 0
    tokens_out: int = 0
    gen_time_ms: int = 0
    heuristic_score: Optional[float] = None            # 0..1
    
    # NEW: Additional metadata from your test results
    estimated_cost: Optional[float] = None             # Cost estimate
    performance_tier: Optional[Literal["fast", "medium", "slow"]] = None


class JudgeScores(BaseModel):
    """Scores for one candidate."""
    by_trait: Dict[str, float]                         # trait -> 0..1
    explanation: Optional[str] = None
    confidence: float = 0.0                            # 0..1 aggregate confidence


class EvidenceSource(TypedDict, total=False):
    id: str
    type: str                                          # "web","kb","api"
    uri: str                                           # normalized URL/identifier
    snippet: str


class Evidence(BaseModel):
    claim_id: str
    text: Optional[str] = None
    status: Literal["Verified", "Weak", "Failed", "NotChecked"]
    sources: List[EvidenceSource] = []
    notes: Optional[str] = None


# ---- Response models ----
class RouteResponse(BaseModel):
    pipeline_id: PipelineID
    decision_reason: str                               # why dispatcher picked this pipeline
    answer: str

    # Winner/info common fields
    winner_model: Optional[str] = None
    confidence: Optional[float] = None                 # 0..1 overall confidence
    
    # NEW: Performance metadata
    response_time_ms: Optional[int] = None             # Total response time
    models_attempted: Optional[List[str]] = None       # All models that were tried
    models_succeeded: Optional[List[str]] = None       # Models that returned results

    # Judge-specific (present when pipeline_id == "judge")
    scores_by_trait: Optional[Dict[str, float]] = None

    # Tool-chain-specific (present when pipeline_id == "tool_chain")
    evidence: Optional[List[Evidence]] = None

    # Citations are always included (may be empty)
    citations: List[Dict[str, Any]] = []

    # Trace id for observability
    trace_id: str


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    # NEW: Health details
    available_models: Optional[int] = None
    last_test_time: Optional[str] = None