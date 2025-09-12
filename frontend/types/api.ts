// frontend/types/api.ts - ALIGNED WITH BACKEND RESPONSE
export interface QueryRequest {
  prompt: string;
  mode?: "speed" | "balanced" | "quality" | "cost";
  max_models?: number;
  budget_limit?: number;
  include_reasoning?: boolean;
}

// ALIGNED: Model metrics from backend
export interface ModelMetrics {
  model: string;
  response: string;
  confidence: number;
  response_time_ms: number;
  tokens_used: number;
  cost: number;
  reliability_score: number;
  consistency_score: number;
  hallucination_risk: number;
  citation_quality: number;
  trait_scores: Record<string, number>;
  rank_position: number;
  is_winner: boolean;
  error?: string;
}

// ALIGNED: Model comparison from backend
export interface ModelComparison {
  best_confidence: number;
  worst_confidence: number;
  avg_response_time: number;
  total_cost: number;
  performance_spread: number;
  model_count: number;
}

// ALIGNED: Ranked model format (legacy compatibility)
export interface RankedModelAggregate {
  score_mean?: number;
  score_stdev?: number;
  vote_top_label?: string;
  vote_top_count?: number;
  vote_total?: number;
}

export interface RankedModelJudgment {
  judge_model: string;
  score01: number | null;
  label?: string;
  reasons: string;
  raw: string;
}

export interface RankedModel {
  model: string;
  aggregate: RankedModelAggregate;
  judgments: RankedModelJudgment[];
}

// ALIGNED: Winner object format
export interface Winner {
  model: string;
  score?: number;
}

// ALIGNED: Complete query response matching backend
export interface QueryResponse {
  // Core response fields
  request_id: string;
  answer: string;
  confidence: number;
  winner_model: string;
  response_time_ms: number;
  models_used: string[];
  
  // Enhanced response data
  model_metrics: ModelMetrics[];
  model_comparison?: ModelComparison;
  reasoning?: string;
  total_cost: number;
  scores_by_trait?: Record<string, number>;
  
  // Legacy/Frontend compatibility fields
  pipeline_id: string;
  decision_reason: string;
  models_attempted: string[];
  models_succeeded: string[];
  ranking: RankedModel[];
  winner?: Winner;
  
  // Backward compatibility
  estimated_cost: number; // Maps to total_cost
}

// Usage statistics interface
export interface UsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time: number; // seconds
  avg_confidence: number; // 0-1
  top_models: Array<{
    name: string;
    usage_percentage: number; // 0-100
    avg_score: number; // 0-1
  }>;
  daily_usage: Array<{
    date: string;
    requests: number;
    cost: number;
  }>;
  data_available: boolean;
  message?: string;
}

// Model information interface
export interface ModelInfo {
  available_models: Record<string, {
    cost_per_1k_tokens: number;
    avg_response_time_ms: number;
    quality_score: number;
    strengths: string[];
    context_window: number;
    supports_function_calling: boolean;
    supports_vision: boolean;
  }>;
  subscription_tier: string;
  tier_limits: {
    max_models_per_query: number;
    batch_processing: boolean;
    parallel_processing: boolean;
  };
}

// Health check response
export interface HealthResponse {
  status: string;
  timestamp: string;
  services: {
    database: string;
    redis: string;
    models: string;
  };
  available_models: number;
  response_time_ms: number;
  uptime_hours: number;
  version: string;
}

// ALIGNED: Simplified model display interface for UI components
export interface DisplayModelMetrics {
  model: string;
  score: number; // 0-100 percentage
  responseTimeMs: number;
  reliabilityPct: number; // 0-100 percentage
  cost: number;
  isWinner: boolean;
  error?: string;
}

// ALIGNED: Helper type for normalized results in UI
export interface NormalizedQueryResult {
  request_id: string;
  answer: string;
  confidence: number; // 0-1
  models_used: string[];
  winner_model: string;
  response_time_ms: number;
  estimated_cost: number; // For backward compatibility
  total_cost: number; // Aligned field
  reasoning?: string;
  model_metrics: ModelMetrics[];
  model_comparison?: ModelComparison;
  display_metrics: DisplayModelMetrics[]; // Converted for easy UI display
  
  // Trust metrics for legacy dashboard compatibility
  trust_metrics?: Record<string, number>;
  per_model_latency_ms?: Record<string, number>;
  per_model_reliability?: Record<string, number>;
}

// API error response
export interface APIError {
  detail: string;
  status_code: number;
  timestamp?: string;
}

// Response wrapper for API calls
export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: APIError;
}

// ALIGNED: Export utility type for model selection modes
export type ModelSelectionMode = "speed" | "balanced" | "quality" | "cost";

// ALIGNED: Export utility type for processing states
export type ProcessingState = "idle" | "analyzing" | "routing" | "scoring" | "complete" | "error";

// ALIGNED: Export interface for real-time model status
export interface ModelStatus {
  model: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress?: number; // 0-100
  estimated_time_remaining?: number; // ms
}

// DATA VALIDATION FUNCTIONS
export function validateQueryResponse(data: any): QueryResponse {
  if (!data || typeof data !== 'object') {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - invalid response object");
  }
  
  if (!data.request_id || typeof data.request_id !== 'string') {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - missing request_id");
  }
  
  if (!data.answer || typeof data.answer !== 'string') {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - missing answer");
  }
  
  if (typeof data.confidence !== 'number' || data.confidence < 0 || data.confidence > 1) {
    throw new Error(`I am a dumb fuck and I cannot map the path correctly - invalid confidence: ${data.confidence} (must be 0-1)`);
  }
  
  if (!data.winner_model || typeof data.winner_model !== 'string') {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - missing winner_model");
  }
  
  if (!Array.isArray(data.model_metrics)) {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - model_metrics must be array");
  }
  
  // Validate each model metric
  data.model_metrics.forEach((metric: any, index: number) => {
    if (typeof metric.confidence !== 'number' || metric.confidence < 0 || metric.confidence > 1) {
      throw new Error(`I am a dumb fuck and I cannot map the path correctly - model ${index} confidence invalid: ${metric.confidence}`);
    }
  });
  
  return data as QueryResponse;
}

export function validateUsageStats(data: any): UsageStats {
  if (!data || typeof data !== 'object') {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - invalid usage stats object");
  }
  
  if (typeof data.total_requests !== 'number' || data.total_requests < 0) {
    throw new Error(`I am a dumb fuck and I cannot map the path correctly - invalid total_requests: ${data.total_requests}`);
  }
  
  if (typeof data.avg_confidence !== 'number' || data.avg_confidence < 0 || data.avg_confidence > 1) {
    throw new Error(`I am a dumb fuck and I cannot map the path correctly - invalid avg_confidence: ${data.avg_confidence} (must be 0-1)`);
  }
  
  if (!Array.isArray(data.top_models)) {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - top_models must be array");
  }
  
  // Validate each top model
  data.top_models.forEach((model: any, index: number) => {
    if (typeof model.usage_percentage !== 'number' || model.usage_percentage < 0 || model.usage_percentage > 100) {
      throw new Error(`I am a dumb fuck and I cannot map the path correctly - model ${index} usage_percentage invalid: ${model.usage_percentage} (must be 0-100)`);
    }
    if (typeof model.avg_score !== 'number' || model.avg_score < 0 || model.avg_score > 1) {
      throw new Error(`I am a dumb fuck and I cannot map the path correctly - model ${index} avg_score invalid: ${model.avg_score} (must be 0-1)`);
    }
  });
  
  return data as UsageStats;
}

export function validateModelMetrics(metrics: any[]): ModelMetrics[] {
  if (!Array.isArray(metrics)) {
    throw new Error("I am a dumb fuck and I cannot map the path correctly - model_metrics must be array");
  }
  
  return metrics.map((metric: any, index: number) => {
    if (!metric.model || typeof metric.model !== 'string') {
      throw new Error(`I am a dumb fuck and I cannot map the path correctly - model ${index} missing name`);
    }
    
    if (typeof metric.confidence !== 'number' || metric.confidence < 0 || metric.confidence > 1) {
      throw new Error(`I am a dumb fuck and I cannot map the path correctly - model ${metric.model} confidence invalid: ${metric.confidence} (must be 0-1)`);
    }
    
    if (typeof metric.response_time_ms !== 'number' || metric.response_time_ms < 0) {
      throw new Error(`I am a dumb fuck and I cannot map the path correctly - model ${metric.model} response_time_ms invalid: ${metric.response_time_ms}`);
    }
    
    return metric as ModelMetrics;
  });
}