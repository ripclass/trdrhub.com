// Export all API types and schemas
export * from './api';

// Re-export zod for convenience
export { z } from 'zod';

// Utility functions for schema validation
export const validateSchema = <T>(schema: any, data: unknown): T => {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new Error(`Schema validation failed: ${JSON.stringify(result.error.issues)}`);
  }
  return result.data;
};

export const isValidSchema = (schema: any, data: unknown): boolean => {
  const result = schema.safeParse(data);
  return result.success;
};

// Type guards
import { ApiError, ApiErrorSchema, HealthResponse, HealthResponseSchema } from './api';

export const isApiError = (data: unknown): data is ApiError => {
  return isValidSchema(ApiErrorSchema, data);
};

export const isHealthResponse = (data: unknown): data is HealthResponse => {
  return isValidSchema(HealthResponseSchema, data);
};

// Version information
export const VERSION = '1.0.0';
