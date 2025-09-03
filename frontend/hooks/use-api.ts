// frontend/hooks/use-query.ts
import { useState, useEffect, useCallback } from 'react';
import type { UsageStats } from '@/types/api'; 
import { apiClient, type QueryRequest } from '@/lib/api/client';
import type { QueryResponse, AsyncJobResponse } from '@/lib/api/schemas';

interface UseQueryResult {
  executeQuery: (request: QueryRequest) => Promise<QueryResponse>;
  result: QueryResponse | null;
  loading: boolean;
  progress: AsyncJobResponse | null;
  error: string | null;
  reset: () => void;
}

export function useQuery(): UseQueryResult {
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<AsyncJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const executeQuery = useCallback(async (request: QueryRequest) => {
    setLoading(true);
    setError(null);
    setProgress(null);
    setResult(null);

    try {
      const response = await apiClient.query(request, {
        onProgress: (status) => {
          setProgress(status);
        },
      });

      setResult(response);
      setProgress(null);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Query failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setLoading(false);
    setProgress(null);
    setError(null);
  }, []);

  return {
    executeQuery,
    result,
    loading,
    progress,
    error,
    reset,
  };
}

// Hook for usage statistics with proper validation
export function useUsageStats(days: number = 30) {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await apiClient.getUsageStats(days);
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch usage stats:', err);
      setError(err instanceof Error ? err.message : 'Failed to load statistics');
      
      // Use fallback data if API is unavailable
      setStats({
        total_requests: 0,
        total_tokens: 0,
        total_cost: 0,
        avg_response_time: 0,
        avg_confidence: 0,
        top_models: [],
        daily_usage: [],
        data_available: false,
      });
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
}

// Hook for health check with auto-retry
export function useHealthCheck(intervalMs: number = 30000) {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const healthy = await apiClient.healthCheck();
      setIsHealthy(healthy);
      setLastChecked(new Date());
    } catch {
      setIsHealthy(false);
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    checkHealth();
    
    const interval = setInterval(checkHealth, intervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, intervalMs]);

  return { isHealthy, lastChecked, checkHealth };
}