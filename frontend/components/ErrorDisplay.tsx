import React from 'react';
import { AlertTriangle, RefreshCw, Wifi, Key, Server, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';

interface ErrorDisplayProps {
  error: string | null;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

export function ErrorDisplay({ error, onRetry, isRetrying = false, className = "" }: ErrorDisplayProps) {
  if (!error) return null;

  // Parse error type and provide user-friendly messages
  const getErrorInfo = (error: string) => {
    const errorLower = error.toLowerCase();
    
    if (errorLower.includes('authentication') || errorLower.includes('401') || errorLower.includes('403')) {
      return {
        type: 'authentication',
        title: 'Authentication Error',
        message: 'Please check your API key configuration. Make sure your .env.local file contains the correct NEXT_PUBLIC_API_KEY.',
        icon: Key,
        color: 'text-red-500',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200'
      };
    }
    
    if (errorLower.includes('network') || errorLower.includes('fetch') || errorLower.includes('connection')) {
      return {
        type: 'network',
        title: 'Connection Error',
        message: 'Unable to connect to the backend server. Please ensure the backend is running on http://localhost:8000.',
        icon: Wifi,
        color: 'text-orange-500',
        bgColor: 'bg-orange-50',
        borderColor: 'border-orange-200'
      };
    }
    
    if (errorLower.includes('timeout') || errorLower.includes('504')) {
      return {
        type: 'timeout',
        title: 'Request Timeout',
        message: 'The request took too long to complete. This might be due to high server load. Please try again.',
        icon: Server,
        color: 'text-yellow-500',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200'
      };
    }
    
    if (errorLower.includes('validation') || errorLower.includes('422')) {
      return {
        type: 'validation',
        title: 'Validation Error',
        message: 'There was an issue with the request format. Please check your input and try again.',
        icon: AlertCircle,
        color: 'text-blue-500',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200'
      };
    }
    
    // Default error
    return {
      type: 'unknown',
      title: 'Error',
      message: error,
      icon: AlertTriangle,
      color: 'text-red-500',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200'
    };
  };

  const errorInfo = getErrorInfo(error);
  const Icon = errorInfo.icon;

  return (
    <div className={`p-4 ${errorInfo.bgColor} border ${errorInfo.borderColor} rounded-lg ${className}`}>
      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 ${errorInfo.color} mt-0.5 flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <h4 className={`text-sm font-medium ${errorInfo.color} mb-1`}>
            {errorInfo.title}
          </h4>
          <p className="text-sm text-gray-700 mb-3">
            {errorInfo.message}
          </p>
          
          {onRetry && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                disabled={isRetrying}
                className="text-xs"
              >
                {isRetrying ? (
                  <>
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                    Retrying...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Try Again
                  </>
                )}
              </Button>
              
              {errorInfo.type === 'authentication' && (
                <span className="text-xs text-gray-500">
                  Check your .env.local file
                </span>
              )}
              
              {errorInfo.type === 'network' && (
                <span className="text-xs text-gray-500">
                  Ensure backend is running on port 8000
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Specialized error displays for different contexts
export function QueryErrorDisplay({ error, onRetry, isRetrying }: { error: string | null; onRetry?: () => void; isRetrying?: boolean }) {
  return (
    <ErrorDisplay 
      error={error} 
      onRetry={onRetry} 
      isRetrying={isRetrying}
      className="mb-4"
    />
  );
}

export function StatsErrorDisplay({ error, onRetry, isRetrying }: { error: string | null; onRetry?: () => void; isRetrying?: boolean }) {
  return (
    <ErrorDisplay 
      error={error} 
      onRetry={onRetry} 
      isRetrying={isRetrying}
      className="text-xs"
    />
  );
}
