// frontend/lib/env.ts - ENVIRONMENT VARIABLE VALIDATION
interface EnvConfig {
  NEXT_PUBLIC_API_URL: string;
  NEXT_PUBLIC_BACKEND_URL: string;
  NEXT_PUBLIC_API_KEY: string;
  NODE_ENV: string;
}

interface EnvValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  config: Partial<EnvConfig>;
}

class EnvValidator {
  private requiredVars: (keyof EnvConfig)[] = [
    'NEXT_PUBLIC_API_URL',
    'NEXT_PUBLIC_BACKEND_URL'
  ];

  private optionalVars: (keyof EnvConfig)[] = [
    'NEXT_PUBLIC_API_KEY',
    'NODE_ENV'
  ];

  private defaultValues: Partial<EnvConfig> = {
    NEXT_PUBLIC_API_URL: 'http://localhost:8000',
    NEXT_PUBLIC_BACKEND_URL: 'http://localhost:8000',
    NEXT_PUBLIC_API_KEY: 'nextagi_test-key-123',
    NODE_ENV: 'development'
  };

  validate(): EnvValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    const config: Partial<EnvConfig> = {};

    // Check required variables
    for (const varName of this.requiredVars) {
      const value = process.env[varName];
      if (!value) {
        errors.push(`Missing required environment variable: ${varName}`);
        config[varName] = this.defaultValues[varName] as string;
      } else {
        config[varName] = value;
      }
    }

    // Check optional variables
    for (const varName of this.optionalVars) {
      const value = process.env[varName];
      if (!value) {
        warnings.push(`Missing optional environment variable: ${varName}`);
        config[varName] = this.defaultValues[varName] as string;
      } else {
        config[varName] = value;
      }
    }

    // Validate URL format
    if (config.NEXT_PUBLIC_API_URL) {
      try {
        new URL(config.NEXT_PUBLIC_API_URL);
      } catch {
        errors.push(`Invalid URL format for NEXT_PUBLIC_API_URL: ${config.NEXT_PUBLIC_API_URL}`);
      }
    }

    if (config.NEXT_PUBLIC_BACKEND_URL) {
      try {
        new URL(config.NEXT_PUBLIC_BACKEND_URL);
      } catch {
        errors.push(`Invalid URL format for NEXT_PUBLIC_BACKEND_URL: ${config.NEXT_PUBLIC_BACKEND_URL}`);
      }
    }

    // Validate API key format
    if (config.NEXT_PUBLIC_API_KEY && config.NEXT_PUBLIC_API_KEY.length < 10) {
      warnings.push('NEXT_PUBLIC_API_KEY seems too short for a secure key');
    }

    // Check for development vs production settings
    if (config.NODE_ENV === 'production') {
      if (config.NEXT_PUBLIC_API_URL?.includes('localhost')) {
        errors.push('Cannot use localhost URL in production environment');
      }
      if (config.NEXT_PUBLIC_API_KEY === 'nextagi_test-key-123') {
        errors.push('Cannot use default test API key in production');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      config
    };
  }

  logValidation(): void {
    const result = this.validate();
    
    console.group('🔧 Environment Configuration');
    
    if (result.isValid) {
      console.log('✅ Environment configuration is valid');
    } else {
      console.error('❌ Environment configuration has errors');
    }

    if (result.errors.length > 0) {
      console.group('🚨 Errors');
      result.errors.forEach(error => console.error(`  • ${error}`));
      console.groupEnd();
    }

    if (result.warnings.length > 0) {
      console.group('⚠️ Warnings');
      result.warnings.forEach(warning => console.warn(`  • ${warning}`));
      console.groupEnd();
    }

    console.group('📋 Current Configuration');
    Object.entries(result.config).forEach(([key, value]) => {
      const displayValue = key.includes('KEY') ? 
        `${value?.substring(0, 12)}...` : 
        value;
      console.log(`  ${key}: ${displayValue}`);
    });
    console.groupEnd();

    console.groupEnd();
  }

  getConfig(): EnvConfig {
    const result = this.validate();
    if (!result.isValid) {
      console.error('Environment validation failed:', result.errors);
      throw new Error(`Environment validation failed: ${result.errors.join(', ')}`);
    }
    return result.config as EnvConfig;
  }
}

// Create singleton instance
const envValidator = new EnvValidator();

// Export validated configuration
export const envConfig = envValidator.getConfig();

// Export validator for runtime checks
export { envValidator };

// Export individual config values for convenience
export const API_BASE_URL = envConfig.NEXT_PUBLIC_API_URL || envConfig.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
export const API_KEY = envConfig.NEXT_PUBLIC_API_KEY || 'nextagi_test-key-123';
export const NODE_ENV = envConfig.NODE_ENV || 'development';

// Log validation on import (only in development)
if (typeof window !== 'undefined' && NODE_ENV === 'development') {
  envValidator.logValidation();
}

// Helper function to check if we're in development
export const isDevelopment = NODE_ENV === 'development';

// Helper function to check if we're in production
export const isProduction = NODE_ENV === 'production';

// Helper function to get API URL with fallback
export const getApiUrl = (): string => {
  return API_BASE_URL;
};

// Helper function to get API key with fallback
export const getApiKey = (): string => {
  return API_KEY;
};
