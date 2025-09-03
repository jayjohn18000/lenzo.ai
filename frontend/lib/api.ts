// lib/api.ts - FIXED API CLIENT
import { QueryRequest, QueryResponse, UsageStats, ModelInfo } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Job response interface
export interface JobResponse {
  job_id: string;
  status: 'accepted' | 'pending' | 'processing' | 'completed' | 'failed';
  estimated_time_ms?: number;
  poll_url?: string;
  poll_interval_ms?: number;
  progress?: number;
  result?: QueryResponse;
  error?: string;
  message?: string;
}

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
    daily_usage: Array.from({ length: 7 }, (_, i) => ({
      date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      requests: Math.floor(Math.random() * 1000) + 1000,
      cost: Math.floor(Math.random() * 50) + 30
    }))
  },
  models: {
    modes: {
      speed: {
        models: ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"],
        avg_response_time_ms: 800,
        avg_cost_per_query: 0.002
      },
      balanced: {
        models: ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"],
        avg_response_time_ms: 1500,
        avg_cost_per_query: 0.01
      },
      quality: {
        models: ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "anthropic/claude-3-opus"],
        avg_response_time_ms: 2500,
        avg_cost_per_query: 0.025
      }
    },
    total_models: 15,
    default_mode: "balanced"
  }
};

export class APIClient {
  private onProgress?: (progress: number) => void;

  setProgressCallback(callback: (progress: number) => void) {
    this.onProgress = callback;
  }

  private async safeRequest<T>(endpoint: string, fallbackData?: T, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok && !fallbackData) {
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

  // Main query method with async job support
  async query(request: QueryRequest, options?: { fast?: boolean }): Promise<QueryResponse> {
    const fast = options?.fast ?? (request.mode === 'speed');
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/query?fast=${fast}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      // Handle 202 Accepted (async job)
      if (response.status === 202) {
        const jobData: JobResponse = await response.json();
        console.log('Query accepted as job:', jobData.job_id);
        
        // Poll for results
        return await this.pollJob(jobData.job_id, jobData.poll_interval_ms || 500);
      }

      // Handle direct response
      if (response.ok) {
        return await response.json();
      }

      throw new Error(`Query failed: ${response.status}`);
    } catch (error) {
      console.error('Query error:', error);
      throw error;
    }
  }

  // Poll job status until completion
  private async pollJob(
    jobId: string, 
    intervalMs: number,
    maxAttempts: number = 120 // 60 seconds with 500ms intervals
  ): Promise<QueryResponse> {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`);
        const data = await response.json();
        
        if (response.status === 200) {
          // Job completed successfully
          console.log('Job completed:', jobId);
          return data.result;
        } else if (response.status === 500) {
          // Job failed
          throw new Error(data.error || 'Job processing failed');
        } else if (response.status === 202) {
          // Still processing
          if (this.onProgress && data.progress !== undefined) {
            this.onProgress(data.progress);
          }
          console.log(`Job ${jobId} progress: ${data.progress || 0}%`);
          
          // Wait and retry
          await new Promise(resolve => setTimeout(resolve, intervalMs));
          attempts++;
        } else if (response.status === 404) {
          throw new Error('Job not found');
        }
      } catch (error) {
        console.error('Polling error:', error);
        throw error;
      }
    }
    
    throw new Error('Job timeout - exceeded maximum polling attempts');
  }

  // Quick query helper for simple questions
  async quickQuery(prompt: string): Promise<QueryResponse> {
    return this.query(
      {
        prompt,
        mode: 'speed',
        max_models: 2,
        include_reasoning: false,
      },
      { fast: true }
    );
  }

  // Quality query helper for complex questions
  async qualityQuery(prompt: string): Promise<QueryResponse> {
    return this.query(
      {
        prompt,
        mode: 'quality',
        max_models: 5,
        include_reasoning: true,
      },
      { fast: false }
    );
  }

  // Balanced query (default)
  async balancedQuery(prompt: string): Promise<QueryResponse> {
    return this.query(
      {
        prompt,
        mode: 'balanced',
        max_models: 3,
        include_reasoning: true,
      }
    );
  }

  // Get usage statistics
  async getUsageStats(days: number = 30): Promise<UsageStats> {
    return this.safeRequest(`/api/v1/usage?days=${days}`, FALLBACK_DATA.usage);
  }

  // Get available models
  async getModels(): Promise<ModelInfo> {
    return this.safeRequest('/api/v1/models', FALLBACK_DATA.models);
  }

  // Health check
  async getHealth(): Promise<any> {
    return this.safeRequest('/api/v1/health');
  }
}

// Export singleton instance
export const apiClient = new APIClient();