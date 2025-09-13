import { useState, useEffect } from 'react';

export interface ModelPerformance {
  top_models: Array<{
    name: string;
    usage_percentage: number;
    avg_score: number;
    avg_response_time: number;
    win_rate: number;
  }>;
  period_days: number;
  last_updated: string;
}

export function useModelPerformance() {
  const [data, setData] = useState<ModelPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/models/performance');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        setData(data);
      } catch (err) {
        console.error('Failed to fetch model performance:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch model performance');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh every 2 minutes
    const interval = setInterval(fetchData, 120000);
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: () => {
    setLoading(true);
    setError(null);
    fetch('/api/models/performance').then(response => response.json()).then(setData).catch(setError).finally(() => setLoading(false));
  }};
}
