// frontend/lib/env-config.ts - ENVIRONMENT CONFIGURATION
// This file provides type-safe access to environment variables

interface EnvironmentConfig {
  NEXT_PUBLIC_API_URL: string;
  NEXT_PUBLIC_BACKEND_URL: string;
  NEXT_PUBLIC_API_KEY: string;
  NODE_ENV: string;
}

// Get environment variables with fallbacks
export const env: EnvironmentConfig = {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  NEXT_PUBLIC_API_KEY: process.env.NEXT_PUBLIC_API_KEY || 'nextagi_test-key-123',
  NODE_ENV: process.env.NODE_ENV || 'development'
};

// Helper functions
export const isDevelopment = env.NODE_ENV === 'development';
export const isProduction = env.NODE_ENV === 'production';
export const getApiUrl = () => env.NEXT_PUBLIC_API_URL || env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
export const getApiKey = () => env.NEXT_PUBLIC_API_KEY || 'nextagi_test-key-123';
