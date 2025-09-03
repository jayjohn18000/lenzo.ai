// frontend/lib/api/schemas.ts
import { z } from 'zod';

// Numeric field schema with string coercion
const NumericField = z.union([
  z.number(),
  z.string().transform(val => parseFloat(val))
]).refine(val => !isNaN(val) && isFinite(val), {
  message: "Must be a valid number"
});

// Model metrics schema
export const ModelMetricsSchema = z.object({
  model: z.string(),
  confidence: NumericField.optional().default(0),
  response_time_ms: NumericField.optional().default(0),
  cost: NumericField.optional().default(0),
  reliability_score: NumericField.optional().default(0),
  hallucination_risk: NumericField.optional().default(0),
  consistency_score: NumericField.optional().default(0),
  citation_quality: NumericField.optional().default(0),
});

// Synchronous query response (full result)
export const QueryResponseSchema = z.object({
  request_id: z.string(),
  status: z.literal('completed').optional(),
  answer: z.string(),
  confidence: NumericField,
  models_used: z.array(z.string()),
  winner_model: z.string(),
  response_time_ms: NumericField,
  total_cost: NumericField.optional(),
  estimated_cost: NumericField.optional(),
  model_metrics: z.array(ModelMetricsSchema).optional(),
  trust_metrics: z.record(z.string(), NumericField).optional(),
  citations: z.array(z.any()).optional(),
});

// Asynchronous job response (202 Accepted)
export const AsyncJobResponseSchema = z.object({
  job_id: z.string(),
  status: z.enum(['queued', 'processing', 'completed', 'failed']),
  estimated_time_ms: NumericField.optional(),
  queue_position: z.number().optional(),
  message: z.string().optional(),
});

// Union type for query endpoint responses
export const QueryEndpointResponseSchema = z.discriminatedUnion('status', [
  QueryResponseSchema.extend({ status: z.literal('completed') }),
  AsyncJobResponseSchema.extend({ status: z.enum(['queued', 'processing']) }),
]);

// Usage stats schemas
export const ModelUsageSchema = z.object({
  name: z.string(),
  usage_percentage: NumericField,
  avg_score: NumericField.optional().default(0),
  avg_response_time: NumericField.optional().default(0),
});

export const DailyUsageSchema = z.object({
  date: z.string(),
  requests: z.number(),
  cost: NumericField,
});

export const UsageStatsSchema = z.object({
  total_requests: z.number(),
  total_tokens: z.number().optional().default(0),
  total_cost: NumericField,
  avg_response_time: NumericField,
  avg_confidence: NumericField,
  top_models: z.array(ModelUsageSchema),
  daily_usage: z.array(DailyUsageSchema).optional().default([]),
  data_available: z.boolean().optional().default(true),
});

// Type exports
export type QueryResponse = z.infer<typeof QueryResponseSchema>;
export type AsyncJobResponse = z.infer<typeof AsyncJobResponseSchema>;
export type QueryEndpointResponse = z.infer<typeof QueryEndpointResponseSchema>;
export type UsageStats = z.infer<typeof UsageStatsSchema>;
export type ModelMetrics = z.infer<typeof ModelMetricsSchema>;