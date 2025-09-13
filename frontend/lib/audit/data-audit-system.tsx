// data-audit-system.ts
// A comprehensive system for auditing data validation issues in your application

import { z } from 'zod';
import React from 'react';

// ============================================
// 1. RUNTIME DATA LOGGER
// ============================================

interface DataFlowLog {
  timestamp: Date;
  location: string;
  dataType: 'api-response' | 'props' | 'state' | 'context';
  data: any;
  validation: {
    passed: boolean;
    errors?: string[];
    warnings?: string[];
  };
  metadata?: Record<string, any>;
}

class DataAuditor {
  private logs: DataFlowLog[] = [];
  private issues: Map<string, { count: number; samples: any[] }> = new Map();
  
  constructor(private options: {
    logToConsole?: boolean;
    logToFile?: boolean;
    maxSamples?: number;
  } = {}) {
    this.options = {
      logToConsole: true,
      logToFile: false,
      maxSamples: 5,
      ...options
    };
  }

  // Log any data crossing boundaries
  logDataFlow(params: {
    location: string;
    dataType: DataFlowLog['dataType'];
    data: any;
    expectedSchema?: z.ZodSchema;
    metadata?: Record<string, any>;
  }) {
    const { location, dataType, data, expectedSchema, metadata } = params;
    
    const log: DataFlowLog = {
      timestamp: new Date(),
      location,
      dataType,
      data: this.sanitizeData(data),
      validation: { passed: true },
      metadata
    };

    // Validate against schema if provided
    if (expectedSchema) {
      try {
        expectedSchema.parse(data);
      } catch (error) {
        if (error instanceof z.ZodError) {
          log.validation.passed = false;
          log.validation = log.validation ?? {};
          log.validation.errors = error.issues.map(i => i.message);
        }
      }
    }

    // Check for common issues
    const warnings = this.detectCommonIssues(data, location);
    if (warnings.length > 0) {
      log.validation.warnings = warnings;
    }

    this.logs.push(log);
    
    // Track issues
    if (!log.validation.passed || (log.validation.warnings && log.validation.warnings.length > 0)) {
      const issueKey = `${location}:${dataType}`;
      const issue = this.issues.get(issueKey) || { count: 0, samples: [] };
      issue.count++;
      
      if (issue.samples.length < (this.options.maxSamples || 5)) {
        issue.samples.push({
          timestamp: log.timestamp,
          data: log.data,
          errors: log.validation.errors,
          warnings: log.validation.warnings
        });
      }
      
      this.issues.set(issueKey, issue);
    }

    if (this.options.logToConsole && (!log.validation.passed || log.validation.warnings)) {
      console.warn(`[DataAudit] ${location}`, log);
    }

    return log;
  }

  // Detect common data validation issues
  private detectCommonIssues(data: any, location: string): string[] {
    const warnings: string[] = [];

    // Check for undefined/null in expected numeric fields
    if (location.includes('cost') || location.includes('price') || location.includes('amount')) {
      if (data === undefined) warnings.push('Numeric field is undefined');
      if (data === null) warnings.push('Numeric field is null');
      if (typeof data === 'string') warnings.push('Numeric field is string type');
    }

    // Check for missing required fields in objects
    if (typeof data === 'object' && data !== null) {
      const checkFields = (obj: any, path: string = '') => {
        for (const [key, value] of Object.entries(obj)) {
          const fullPath = path ? `${path}.${key}` : key;
          
          if (value === undefined) {
            warnings.push(`Field '${fullPath}' is undefined`);
          }
          
          // Check for .toFixed() usage on non-numbers
          if (key.includes('cost') || key.includes('price') || key.includes('time')) {
            if (value !== null && value !== undefined && typeof value !== 'number') {
              warnings.push(`Field '${fullPath}' expected to be number but is ${typeof value}`);
            }
          }
          
          // Recursively check nested objects
          if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            checkFields(value, fullPath);
          }
        }
      };
      
      checkFields(data);
    }

    return warnings;
  }

  // Sanitize sensitive data
  private sanitizeData(data: any): any {
    if (!data) return data;
    
    const sensitiveKeys = ['password', 'token', 'secret', 'key', 'authorization'];
    
    if (typeof data === 'object') {
      const sanitized = Array.isArray(data) ? [...data] : { ...data };
      
      for (const key in sanitized) {
        if (sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
          sanitized[key] = '[REDACTED]';
        } else if (typeof sanitized[key] === 'object') {
          sanitized[key] = this.sanitizeData(sanitized[key]);
        }
      }
      
      return sanitized;
    }
    
    return data;
  }

  // Generate audit report
  generateReport(): AuditReport {
    const report: AuditReport = {
      summary: {
        totalLogs: this.logs.length,
        totalIssues: this.issues.size,
        issuesByType: new Map(),
        mostCommonIssues: []
      },
      issues: Array.from(this.issues.entries()).map(([key, value]) => ({
        location: key,
        count: value.count,
        samples: value.samples
      })),
      recommendations: this.generateRecommendations()
    };

    // Count issues by type
    for (const log of this.logs) {
      if (!log.validation.passed || log.validation.warnings) {
        const type = log.dataType;
        report.summary.issuesByType.set(
          type, 
          (report.summary.issuesByType.get(type) || 0) + 1
        );
      }
    }

    // Find most common issues
    report.summary.mostCommonIssues = Array.from(this.issues.entries())
      .sort(([, a], [, b]) => b.count - a.count)
      .slice(0, 10)
      .map(([location, { count }]) => ({ location, count }));

    return report;
  }

  // Generate recommendations based on found issues
  private generateRecommendations(): string[] {
    const recommendations: string[] = [];
    
    for (const [location, issue] of this.issues) {
      if (issue.samples.some(s => s.errors?.some((e: string) => e.includes('undefined')))) {
        recommendations.push(`Add null/undefined checks in ${location}`);
      }
      
      if (issue.samples.some(s => s.warnings?.some((w: string) => w.includes('expected to be number')))) {
        recommendations.push(`Add type conversion or validation for numeric fields in ${location}`);
      }
    }
    
    return [...new Set(recommendations)]; // Remove duplicates
  }

  // Export logs for further analysis
  exportLogs(): string {
    return JSON.stringify({
      exportDate: new Date().toISOString(),
      logs: this.logs,
      report: this.generateReport()
    }, null, 2);
  }
}

// ============================================
// 2. API RESPONSE VALIDATOR
// ============================================

// Example schemas for your API responses
const APISchemas = {
  // Define your expected API response structures
  battleResult: z.object({
    winner_model: z.string(),
    total_cost: z.number(), // This was missing/undefined in your error
    response_time_ms: z.number(),
    // Add other expected fields
  }),
  
  // Add more schemas for other API endpoints
  userProfile: z.object({
    id: z.string(),
    name: z.string(),
    email: z.string().email(),
  })
};

// API Response wrapper with validation
export function createAPIValidator(auditor: DataAuditor) {
  return {
    async validateResponse<T>(
      response: Response,
      schema: z.ZodSchema<T>,
      endpoint: string
    ): Promise<{ data?: T; error?: string; rawData?: any }> {
      try {
        const rawData = await response.json();
        
        // Log the raw response
        auditor.logDataFlow({
          location: endpoint,
          dataType: 'api-response',
          data: rawData,
          expectedSchema: schema,
          metadata: {
            status: response.status,
            headers: Object.fromEntries(response.headers.entries())
          }
        });
        
        // Validate against schema
        const validatedData = schema.parse(rawData);
        return { data: validatedData, rawData };
        
      } catch (error) {
        if (error instanceof z.ZodError) {
          return {
            error: `Validation failed: ${error.issues.map(i => i.message).join(', ')}`,
            rawData: undefined
          };
        }
        return { error: `Failed to parse response: ${error}` };
      }
    }
  };
}

// ============================================
// 3. REACT COMPONENT PROP VALIDATOR
// ============================================

export function createPropValidator(auditor: DataAuditor) {
  return function validateProps<T>(
    componentName: string,
    props: T,
    schema?: z.ZodSchema<T>
  ): T {
    auditor.logDataFlow({
      location: `Component:${componentName}`,
      dataType: 'props',
      data: props,
      expectedSchema: schema
    });
    
    return props;
  };
}

// ============================================
// 4. AUDIT REPORT INTERFACE
// ============================================

interface AuditReport {
  summary: {
    totalLogs: number;
    totalIssues: number;
    issuesByType: Map<string, number>;
    mostCommonIssues: { location: string; count: number }[];
  };
  issues: {
    location: string;
    count: number;
    samples: any[];
  }[];
  recommendations: string[];
}

// ============================================
// 5. USAGE EXAMPLE FOR YOUR APP
// ============================================

// Initialize the auditor
const auditor = new DataAuditor({
  logToConsole: true,
  maxSamples: 10
});

// Create validators
const apiValidator = createAPIValidator(auditor);
const propValidator = createPropValidator(auditor);

// Example: Wrapping your fetch calls
export async function fetchWithValidation<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit
) {
  const response = await fetch(url, options);
  return apiValidator.validateResponse(response, schema, url);
}

export function ValidatedComponent<P extends React.JSX.IntrinsicAttributes>(
  Component: React.ComponentType<P>,
  validate: (props: unknown) => P
) {
  return (props: unknown) => {
    const validatedProps = validate(props);
    return <Component {...validatedProps} />;
  };
}

// ============================================
// 6. AUTOMATED CODEBASE SCANNER
// ============================================

export class CodebaseScanner {
  // Patterns to look for potential data validation issues
  private patterns = {
    unsafePropertyAccess: /(\w+)\.(\w+)\.(\w+)/g, // Deep property access
    toFixedUsage: /\.toFixed\(/g,
    parseIntUsage: /parseInt\(/g,
    numberCoercion: /Number\(/g,
    optionalChaining: /\?\./g,
    nullishCoalescing: /\?\?/g,
    typeAssertion: /as\s+\w+/g,
    nonNullAssertion: /\!/g,
  };

  scanFile(content: string, filename: string): ScanResult {
    const issues: ScanIssue[] = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      // Check for unsafe property access
      if (line.match(this.patterns.unsafePropertyAccess) && !line.includes('?.')) {
        issues.push({
          file: filename,
          line: index + 1,
          type: 'unsafe-property-access',
          code: line.trim(),
          suggestion: 'Consider using optional chaining (?.) for deep property access'
        });
      }
      
      // Check for .toFixed usage
      if (line.match(this.patterns.toFixedUsage)) {
        const hasOptionalChaining = line.includes('?.toFixed');
        const hasTypeCheck = line.includes('typeof') && line.includes('number');
        
        if (!hasOptionalChaining && !hasTypeCheck) {
          issues.push({
            file: filename,
            line: index + 1,
            type: 'unsafe-number-method',
            code: line.trim(),
            suggestion: 'Add type check or optional chaining before .toFixed()'
          });
        }
      }
    });
    
    return { filename, issues };
  }
}

interface ScanResult {
  filename: string;
  issues: ScanIssue[];
}

interface ScanIssue {
  file: string;
  line: number;
  type: string;
  code: string;
  suggestion: string;
}

// Export everything
export {
  DataAuditor,
  APISchemas,
  auditor,
  apiValidator,
  propValidator
};