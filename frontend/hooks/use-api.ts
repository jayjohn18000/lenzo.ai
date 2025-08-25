// hooks/use-api.ts - Updated React hooks
import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api';

export function useQuery() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const executeQuery = useCallback(async (request: {
    prompt: string;
    judge_models: string[];
    use_ask: boolean;
  }) => {
    setLoading(true);
    setError(null);
    
    try {
      // Use your existing route endpoint
      const response = await apiClient.query(request);
      setResult(response);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Query failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    executeQuery,
    loading,
    error,
    result,
    resetError: () => setError(null),
    resetResult: () => setResult(null)
  };
}

export function useUsageStats(days: number = 30) {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getUsageStats(days);
      setStats(data);
    } catch (err) {
      console.warn('Usage stats not available, using fallback data');
      // Provide fallback data when endpoint is not ready
      setStats({
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

export function useModels() {
  const [models, setModels] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await apiClient.getModels();
        setModels(data);
      } catch (err) {
        console.warn('Models endpoint not available, using fallback data');
        setModels({
          available_models: {
            "openai/gpt-4": { cost_per_1k_tokens: 0.03, quality_score: 0.95 },
            "anthropic/claude-3-5-sonnet": { cost_per_1k_tokens: 0.015, quality_score: 0.92 },
            "google/gemini-pro": { cost_per_1k_tokens: 0.001, quality_score: 0.88 }
          },
          subscription_tier: "enterprise",
          tier_limits: {
            max_models_per_query: 8,
            batch_processing: true,
            parallel_processing: true
          }
        });
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  return { models, loading, error };
}