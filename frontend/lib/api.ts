// lib/api.ts - FIXED API CLIENT
import { QueryRequest, QueryResponse, UsageStats, ModelInfo, validateQueryResponse, validateUsageStats } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'nextagi_test-key-123';

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

// NO MORE DUMMY DATA - Proper error handling instead
const ERROR_MESSAGES = {
  API_UNAVAILABLE: "I am a dumb fuck and I cannot map the path correctly - API connection failed",
  DATA_VALIDATION_FAILED: "I am a dumb fuck and I cannot map the path correctly - data validation failed",
  NETWORK_ERROR: "I am a dumb fuck and I cannot map the path correctly - network error",
  AUTHENTICATION_FAILED: "I am a dumb fuck and I cannot map the path correctly - authentication failed"
};

export class APIClient {
  private onProgress?: (progress: number) => void;

  setProgressCallback(callback: (progress: number) => void) {
    this.onProgress = callback;
  }

  private async safeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY && { 'Authorization': `Bearer ${API_KEY}` }),
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error(ERROR_MESSAGES.AUTHENTICATION_FAILED);
        }
        throw new Error(`${ERROR_MESSAGES.NETWORK_ERROR} - HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API endpoint ${endpoint} failed:`, error);
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
          ...(API_KEY && { 'Authorization': `Bearer ${API_KEY}` }),
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
        const data = await response.json();
        return validateQueryResponse(data);
      }

      throw new Error(`Query failed: ${response.status}`);
    } catch (error) {
      console.error('Query error:', error);
      if (error instanceof Error && error.message.includes('I am a dumb fuck')) {
        throw error; // Re-throw validation errors as-is
      }
      throw new Error(`${ERROR_MESSAGES.DATA_VALIDATION_FAILED} - ${error}`);
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
        const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
          }
        });
        const data = await response.json();
        
        if (response.status === 200) {
          // Job completed successfully
          console.log('Job completed:', jobId);
          return validateQueryResponse(data.result);
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
    try {
      const data = await this.safeRequest(`/api/v1/usage?days=${days}`);
      return validateUsageStats(data);
    } catch (error) {
      console.error('Usage stats validation failed:', error);
      throw new Error(`${ERROR_MESSAGES.DATA_VALIDATION_FAILED} - ${error}`);
    }
  }

  // Get available models
  async getModels(): Promise<ModelInfo> {
    try {
      return await this.safeRequest('/api/v1/models');
    } catch (error) {
      console.error('Models API failed:', error);
      throw new Error(`${ERROR_MESSAGES.API_UNAVAILABLE} - models endpoint`);
    }
  }

  // Health check
  async getHealth(): Promise<any> {
    return this.safeRequest('/api/v1/health');
  }
}

// Export singleton instance
export const apiClient = new APIClient();