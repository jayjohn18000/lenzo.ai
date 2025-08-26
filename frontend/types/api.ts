// types/api.ts
export interface QueryRequest {
    prompt: string;
    judge_models: string[];
    use_ask: boolean;
  }
  
  export interface QueryResponse {
    request_id?: string;
    pipeline_id: string;
    decision_reason: string;
    answer: string;
    winner_model?: string;
    confidence?: number;
    response_time_ms?: number;
    models_attempted?: string[];
    models_succeeded?: string[];
    ranking?: RankedModel[];
    winner?: {
      model: string;
      score?: number;
    };
  }
  
  export interface RankedModel {
    model: string;
    aggregate: {
      score_mean?: number;
      score_stdev?: number;
      vote_top_label?: string;
      vote_top_count?: number;
      vote_total?: number;
    };
    judgments: Array<{
      judge_model: string;
      score01: number | null;
      label?: string;
      reasons: string;
      raw: string;
    }>;
  }
  
  export interface UsageStats {
    total_requests: number;
    total_tokens: number;
    total_cost: number;
    avg_response_time: number;
    avg_confidence: number;
    top_models: Array<{
      name: string;
      usage_percentage: number;
      avg_score: number;
    }>;
    daily_usage: Array<{
      date: string;
      requests: number;
      cost: number;
    }>;
  }
  
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

  export interface ModelMetrics {
    model: string;
    response: string;
    confidence: number;
    response_time_ms: number;
    cost: number;
    reliability_score: number;
    consistency_score: number;
    hallucination_risk: number;
    citation_quality: number;
    trait_scores: Record<string, number>;
    rank_position: number;
    is_winner: boolean;
  }