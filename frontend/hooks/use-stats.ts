import { useState, useEffect } from 'react';

export interface TodayStats {
  requests: number;
  cost: number;
  avg_confidence: number;
  date: string;
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
    avg_response_time: number;
    win_rate?: number;
  }>;
  daily_usage: Array<{
    date: string;
    requests: number;
    cost: number;
  }>;
  data_available: boolean;
  message?: string;
}

export function useTodayStats() {
  const [data, setData] = useState<TodayStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/usage/today');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        setData(data);
      } catch (err) {
        console.error('Failed to fetch today stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch stats');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: () => {
    setLoading(true);
    setError(null);
    fetch('/api/usage/today').then(response => response.json()).then(setData).catch(setError).finally(() => setLoading(false));
  }};
}

export function useUsageStats(days: number = 7) {
  const [data, setData] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`/api/usage/stats?days=${days}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        setData(data);
      } catch (err) {
        console.error('Failed to fetch usage stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch stats');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [days]);

  return { data, loading, error, refetch: () => {
    setLoading(true);
    setError(null);
    fetch(`/api/usage/stats?days=${days}`).then(response => response.json()).then(setData).catch(setError).finally(() => setLoading(false));
  }};
}
