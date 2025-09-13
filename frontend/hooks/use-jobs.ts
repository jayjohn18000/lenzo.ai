import { useState, useEffect } from 'react';

export interface JobStats {
  pending_jobs: number;
  processing_jobs: number;
  worker_active: boolean;
  total_processed: string;
}

export function useJobStats() {
  const [data, setData] = useState<JobStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/jobs/stats');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        setData(data);
      } catch (err) {
        console.error('Failed to fetch job stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch job stats');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh every 10 seconds for real-time updates
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: () => {
    setLoading(true);
    setError(null);
    fetch('/api/jobs/stats').then(response => response.json()).then(setData).catch(setError).finally(() => setLoading(false));
  }};
}
