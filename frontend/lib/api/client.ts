// frontend/lib/api/client.ts
import { 
    QueryResponseSchema, 
    AsyncJobResponseSchema,
    UsageStatsSchema,
    QueryEndpointResponseSchema,
    type QueryResponse,
    type AsyncJobResponse,
    type UsageStats
  } from './schemas';
import { z } from 'zod';  

  export interface QueryRequest {
    prompt: string;
    mode?: 'fast' | 'balanced' | 'thorough';
    max_models?: number;
    budget_limit?: number;
    fast?: boolean; // Force sync response
  }
  
  export interface QueryOptions {
    onProgress?: (status: AsyncJobResponse) => void;
    pollingInterval?: number;
    maxPollingTime?: number;
  }
  
  export class TypeSafeAPIClient {
    private baseURL: string;
    private apiKey?: string;
  
    constructor(baseURL?: string, apiKey?: string) {
      this.baseURL = baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      this.apiKey = apiKey || process.env.NEXT_PUBLIC_API_KEY;
    }
  
    /**
     * Base request method with automatic validation
     */
    private async request<T>(
      endpoint: string,
      schema: z.ZodSchema<T>,
      options: RequestInit = {}
    ): Promise<T> {
      const url = `${this.baseURL}${endpoint}`;
      
      // Prepare headers with authentication
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
      };
      
      // Add API key authentication for non-dev endpoints
      if (this.apiKey && !endpoint.startsWith('/dev/')) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${this.apiKey}`;
      }
      
      try {
        const response = await fetch(url, {
          ...options,
          headers,
        });
  
        const data = await response.json();
  
        // Handle HTTP errors
        if (!response.ok) {
          throw new APIError(
            data.error || `HTTP ${response.status}`,
            response.status,
            data
          );
        }
  
        // Validate and transform response
        const validated = schema.safeParse(data);
        
        if (!validated.success) {
          console.error('Validation error:', validated.error);
          throw new ValidationError(
            'Invalid response format',
            validated.error
          );
        }
  
        return validated.data;
      } catch (error) {
        if (error instanceof APIError || error instanceof ValidationError) {
          throw error;
        }
        
        console.error('API request failed:', error);
        throw new NetworkError(
          `Failed to fetch ${endpoint}`,
          error
        );
      }
    }
  
    /**
     * Query endpoint with automatic async handling
     */
    async query(
      request: QueryRequest,
      options: QueryOptions = {}
    ): Promise<QueryResponse> {
      // First, make the initial request
      const response = await this.request(
        '/dev/query',
        QueryEndpointResponseSchema,
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      );
  
      // If we get a completed response, return it
      if (response.status === 'completed') {
        return response as QueryResponse;
      }
  
      // Otherwise, we need to poll for the result
      if ('job_id' in response) {
        return this.pollForResult(response.job_id, options);
      }
  
      throw new Error('Unexpected response format');
    }
  
    /**
     * Poll for async job completion
     */
    private async pollForResult(
      jobId: string,
      options: QueryOptions
    ): Promise<QueryResponse> {
      const {
        onProgress,
        pollingInterval = 1000,
        maxPollingTime = 30000,
      } = options;
  
      const startTime = Date.now();
  
      while (Date.now() - startTime < maxPollingTime) {
        await this.sleep(pollingInterval);
  
        try {
          const jobStatus = await this.request(
            `/dev/jobs/${jobId}`,
            AsyncJobResponseSchema
          );
  
          if (onProgress) {
            onProgress(jobStatus);
          }
  
          if (jobStatus.status === 'completed') {
            // Fetch the actual result
            const result = await this.request(
              `/dev/jobs/${jobId}`,
              QueryResponseSchema
            );
            return result;
          }
  
          if (jobStatus.status === 'failed') {
            throw new Error(jobStatus.message || 'Job failed');
          }
        } catch (error) {
          console.error('Polling error:', error);
          // Continue polling on non-fatal errors
        }
      }
  
      throw new Error('Polling timeout exceeded');
    }
  
    /**
     * Get usage statistics with validation
     */
    async getUsageStats(days: number = 30): Promise<UsageStats> {
      return this.request(
        `/api/v1/usage?days=${days}`,
        UsageStatsSchema
      );
    }
    
    /**
     * Get today's statistics for dashboard
     */
    async getTodayStats(): Promise<any> {
      return this.request(
        `/api/v1/usage/today`,
        z.object({
          requests: z.number(),
          cost: z.number(),
          avg_confidence: z.number(),
          date: z.string(),
        })
      );
    }
    
    /**
     * Get model performance statistics
     */
    async getModelPerformance(): Promise<any> {
      return this.request(
        `/api/v1/models/performance`,
        z.object({
          top_models: z.array(z.object({
            name: z.string(),
            usage_percentage: z.number(),
            avg_score: z.number(),
            avg_response_time: z.number(),
            win_rate: z.number(),
          })),
          period_days: z.number(),
          last_updated: z.string(),
        })
      );
    }
    
    /**
     * Get job statistics (admin endpoint)
     */
    async getJobStats(): Promise<any> {
      return this.request(
        `/admin/jobs`,
        z.object({
          pending_jobs: z.number(),
          processing_jobs: z.number(),
          worker_active: z.boolean(),
          total_processed: z.string(),
        })
      );
    }
  
    /**
     * Health check endpoint
     */
    async healthCheck(): Promise<boolean> {
      try {
        const response = await fetch(`${this.baseURL}/dev/health`);
        return response.ok;
      } catch {
        return false;
      }
    }
  
    private sleep(ms: number): Promise<void> {
      return new Promise(resolve => setTimeout(resolve, ms));
    }
  }
  
  // Custom error classes
  export class APIError extends Error {
    constructor(
      message: string,
      public statusCode: number,
      public data?: any
    ) {
      super(message);
      this.name = 'APIError';
    }
  }
  
  export class ValidationError extends Error {
    constructor(
      message: string,
      public validationError: z.ZodError
    ) {
      super(message);
      this.name = 'ValidationError';
    }
  }
  
  export class NetworkError extends Error {
    constructor(
      message: string,
      public originalError?: any
    ) {
      super(message);
      this.name = 'NetworkError';
    }
  }
  
  // Export singleton instance
  export const apiClient = new TypeSafeAPIClient();