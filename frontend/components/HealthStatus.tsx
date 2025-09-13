"use client";

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'checking' | 'error';
  message: string;
  timestamp?: string;
  version?: string;
}

export function HealthStatus() {
  const [health, setHealth] = useState<HealthStatus>({ status: 'checking', message: 'Checking...' });
  const [isVisible, setIsVisible] = useState(false);

  const checkHealth = async () => {
    setHealth({ status: 'checking', message: 'Checking backend health...' });
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/dev/health`, {
        headers: {
          'Content-Type': 'application/json'
          // No authentication required for dev endpoint
        }
      });

      if (response.ok) {
        const data = await response.json();
        setHealth({
          status: 'healthy',
          message: 'Backend is healthy',
          timestamp: new Date().toLocaleTimeString(),
          version: data.version
        });
      } else {
        setHealth({
          status: 'unhealthy',
          message: `Backend returned ${response.status}`,
          timestamp: new Date().toLocaleTimeString()
        });
      }
    } catch (error) {
      setHealth({
        status: 'error',
        message: 'Cannot connect to backend',
        timestamp: new Date().toLocaleTimeString()
      });
    }
  };

  useEffect(() => {
    checkHealth();
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = () => {
    switch (health.status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'unhealthy':
        return <AlertCircle className="h-4 w-4 text-yellow-400" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-400" />;
      default:
        return <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (health.status) {
      case 'healthy':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'unhealthy':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'error':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="flex items-center gap-2">
        <Badge 
          className={`${getStatusColor()} cursor-pointer transition-all duration-200 hover:scale-105`}
          onClick={() => setIsVisible(!isVisible)}
        >
          {getStatusIcon()}
          <span className="ml-1 text-xs">
            {health.status === 'healthy' ? 'Online' : 
             health.status === 'unhealthy' ? 'Issues' : 
             health.status === 'error' ? 'Offline' : 'Checking...'}
          </span>
        </Badge>
        
        {isVisible && (
          <div className="bg-black/80 backdrop-blur-xl border border-white/10 rounded-lg p-3 min-w-[200px]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">Backend Status</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={checkHealth}
                className="h-6 w-6 p-0 text-gray-400 hover:text-white"
              >
                <RefreshCw className="h-3 w-3" />
              </Button>
            </div>
            
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                {getStatusIcon()}
                <span className="text-gray-300">{health.message}</span>
              </div>
              
              {health.version && (
                <div className="text-gray-400">
                  Version: {health.version}
                </div>
              )}
              
              {health.timestamp && (
                <div className="text-gray-400">
                  Last check: {health.timestamp}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
