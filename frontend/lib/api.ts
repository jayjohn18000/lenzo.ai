// lib/api.ts - ACTUAL API CLIENT CLASS
import { QueryRequest, QueryResponse, UsageStats, ModelInfo } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Fallback data for when backend is not ready
const FALLBACK_DATA = {
  usage: {
    total_requests: 2847,
    total_tokens: 1200000,
    total_cost: 247,
    avg_response_time: 1.8,
    avg_confidence: 0.942,
    top_models: [
      { name: 'GPT-4 Turbo', usage_percentage: 42, avg_score: 0.95 },
      { name: 'Claude-3.5 Sonnet', usage_percentage: 31, avg_score: 0.92 },
      { name: 'Gemini Pro', usage_percentage: 18, avg_score: 0.88 },
      { name: 'Others', usage_percentage: 9, avg_score: 0.85 }
    ],
    daily_usage: [
      { date: '2024-01-01', requests: 1200, cost: 45 },
      { date: '2024-01-02', requests: 1850, cost: 52 },
      { date: '2024-01-03', requests: 2100, cost: 38 },
      { date: '2024-01-04', requests: 1900, cost: 41 },
      { date: '2024-01-05', requests: 2400, cost: 35 },
      { date: '2024-01-06', requests: 2200, cost: 28 },
      { date: '2024-01-07', requests: 2847, cost: 32 }
    ]
  },
  models: {
    available_models: {
      "openai/gpt-4": { 
        cost_per_1k_tokens: 0.03, 
        avg_response_time_ms: 2500,
        quality_score: 0.95,
        strengths: ["reasoning", "analysis"],
        context_window: 128000,
        supports_function_calling: true,
        supports_vision: true
      },
      "anthropic/claude-3-5-sonnet": { 
        cost_per_1k_tokens: 0.015, 
        avg_response_time_ms: 1800,
        quality_score: 0.92,
        strengths: ["analysis", "coding"],
        context_window: 200000,
        supports_function_calling: true,
        supports_vision: true
      },
      "google/gemini-pro": { 
        cost_per_1k_tokens: 0.001, 
        avg_response_time_ms: 1200,
        quality_score: 0.88,
        strengths: ["speed", "multilingual"],
        context_window: 32000,
        supports_function_calling: true,
        supports_vision: false
      }
    },
    subscription_tier: "enterprise",
    tier_limits: {
      max_models_per_query: 8,
      batch_processing: true,
      parallel_processing: true
    }
  }
};

export class APIClient {
  private async safeRequest<T>(endpoint: string, fallbackData?: T, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return response.json();
    } catch (error) {
      console.warn(`API endpoint ${endpoint} not available, using fallback data`);
      if (fallbackData) {
        return fallbackData;
      }
      throw error;
    }
  }

  // Your existing /route endpoint
  async query(request: QueryRequest): Promise<any> {
    return this.safeRequest('/route', undefined, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // New endpoints with fallback
  async getUsageStats(days: number = 30): Promise<UsageStats> {
    return this.safeRequest(`/api/v1/usage?days=${days}`, FALLBACK_DATA.usage);
  }

  async getModels(): Promise<ModelInfo> {
    return this.safeRequest('/api/v1/models', FALLBACK_DATA.models);
  }

  async analyzeQuery(prompt: string): Promise<any> {
    return this.safeRequest(`/api/v1/analyze?prompt=${encodeURIComponent(prompt)}`);
  }

  async getDetailedHealth(): Promise<any> {
    return this.safeRequest('/api/v1/health');
  }
}

// Export the singleton instance
export const apiClient = new APIClient();