/**
 * API Contract Integration Tests
 * 
 * These tests validate that the frontend and backend APIs maintain
 * contract compatibility using shared-types as the source of truth.
 */

import { describe, test, expect, beforeAll, afterAll } from '@jest/globals';
import {
  HealthResponse,
  ApiError,
  FileUploadRequest,
  FileUploadResponse,
  OcrJobRequest,
  OcrJobResponse,
  UserProfile,
  AuthToken,
  validateSchema,
  schemas
} from '@shared/types';

// Test API client (would be implemented in actual project)
interface ApiClient {
  get<T>(path: string): Promise<{ status: number; data: T }>;
  post<T>(path: string, data: unknown): Promise<{ status: number; data: T }>;
  put<T>(path: string, data: unknown): Promise<{ status: number; data: T }>;
  delete<T>(path: string): Promise<{ status: number; data: T }>;
}

// Mock API client for testing
const createMockApiClient = (): ApiClient => ({
  async get(path: string) {
    // Mock implementation - would make actual HTTP calls in real tests
    if (path === '/health') {
      return {
        status: 200,
        data: {
          status: 'healthy',
          timestamp: new Date().toISOString(),
          version: '1.0.0',
          services: {
            database: 'connected',
            redis: 'connected'
          }
        }
      };
    }
    
    if (path === '/nonexistent') {
      return {
        status: 404,
        data: {
          error: 'not_found',
          message: 'Endpoint not found',
          timestamp: new Date().toISOString(),
          path: '/nonexistent',
          method: 'GET'
        }
      };
    }
    
    throw new Error(`Mock not implemented for path: ${path}`);
  },
  
  async post(path: string, data: unknown) {
    if (path === '/auth/login') {
      return {
        status: 200,
        data: {
          access_token: 'mock-jwt-token',
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          expires_in: 3600
        }
      };
    }
    
    if (path === '/files/upload') {
      return {
        status: 200,
        data: {
          upload_id: '123e4567-e89b-12d3-a456-426614174000',
          upload_url: 'https://s3.amazonaws.com/bucket/presigned-url',
          fields: {
            key: 'uploads/file.pdf',
            policy: 'base64-encoded-policy'
          },
          expires_at: new Date(Date.now() + 3600000).toISOString()
        }
      };
    }
    
    throw new Error(`Mock not implemented for path: ${path}`);
  },
  
  async put() { throw new Error('Not implemented'); },
  async delete() { throw new Error('Not implemented'); }
});

describe('API Contract Integration Tests', () => {
  let apiClient: ApiClient;
  
  beforeAll(() => {
    apiClient = createMockApiClient();
  });
  
  describe('Health Endpoint Contract', () => {
    test('should return valid HealthResponse', async () => {
      const response = await apiClient.get<HealthResponse>('/health');
      
      expect(response.status).toBe(200);
      
      // Validate response matches shared-types schema
      expect(() => validateSchema(schemas.HealthResponse, response.data)).not.toThrow();
      
      const healthData = response.data;
      expect(healthData.status).toMatch(/^(healthy|unhealthy)$/);
      expect(healthData.timestamp).toBeDefined();
      expect(healthData.version).toBeDefined();
      expect(healthData.services.database).toMatch(/^(connected|disconnected)$/);
    });
    
    test('should handle health endpoint errors with ApiError format', async () => {
      // Test when health endpoint returns error
      const response = await apiClient.get<ApiError>('/nonexistent');
      
      expect(response.status).toBe(404);
      
      // Validate error response matches ApiError schema
      expect(() => validateSchema(schemas.ApiError, response.data)).not.toThrow();
      
      const errorData = response.data;
      expect(errorData.error).toBeDefined();
      expect(errorData.message).toBeDefined();
      expect(errorData.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    });
  });
  
  describe('Authentication Contract', () => {
    test('should return valid AuthToken on login', async () => {
      const loginData = {
        email: 'test@example.com',
        password: 'password123'
      };
      
      const response = await apiClient.post<AuthToken>('/auth/login', loginData);
      
      expect(response.status).toBe(200);
      
      // Validate response matches AuthToken schema
      expect(() => validateSchema(schemas.AuthToken, response.data)).not.toThrow();
      
      const tokenData = response.data;
      expect(tokenData.access_token).toBeDefined();
      expect(tokenData.refresh_token).toBeDefined();
      expect(tokenData.token_type).toBe('bearer');
      expect(tokenData.expires_in).toBeGreaterThan(0);
    });
  });
  
  describe('File Upload Contract', () => {
    test('should return valid FileUploadResponse', async () => {
      const uploadRequest: FileUploadRequest = {
        filename: 'test-document.pdf',
        content_type: 'application/pdf',
        size: 1024000
      };
      
      const response = await apiClient.post<FileUploadResponse>('/files/upload', uploadRequest);
      
      expect(response.status).toBe(200);
      
      // Validate response matches FileUploadResponse schema
      expect(() => validateSchema(schemas.FileUploadResponse, response.data)).not.toThrow();
      
      const uploadData = response.data;
      expect(uploadData.upload_id).toBeDefined();
      expect(uploadData.upload_url).toMatch(/^https?:\/\//);
      expect(uploadData.fields).toBeDefined();
      expect(uploadData.expires_at).toBeDefined();
    });
    
    test('should validate FileUploadRequest schema', () => {
      const validRequest: FileUploadRequest = {
        filename: 'document.pdf',
        content_type: 'application/pdf',
        size: 1024
      };
      
      expect(() => validateSchema(schemas.FileUploadRequest, validRequest)).not.toThrow();
      
      // Test invalid request
      const invalidRequest = {
        filename: 'document.pdf',
        content_type: 'application/pdf',
        size: -1 // Invalid: negative size
      };
      
      expect(() => validateSchema(schemas.FileUploadRequest, invalidRequest)).toThrow();
    });
  });
  
  describe('OCR Job Contract', () => {
    test('should validate OcrJobRequest schema', () => {
      const validRequest: OcrJobRequest = {
        file_id: '123e4567-e89b-12d3-a456-426614174000',
        language: 'eng+ben',
        options: {
          deskew: true,
          remove_background: false,
          enhance_contrast: true
        }
      };
      
      expect(() => validateSchema(schemas.OcrJobRequest, validRequest)).not.toThrow();
    });
    
    test('should validate OcrJobResponse schema', () => {
      const validResponse: OcrJobResponse = {
        job_id: '123e4567-e89b-12d3-a456-426614174000',
        file_id: '123e4567-e89b-12d3-a456-426614174001',
        status: 'completed',
        result: {
          text: 'Extracted text content',
          confidence: 95.5,
          language_detected: 'eng',
          processing_time_ms: 2500,
          word_count: 150,
          character_count: 750
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        completed_at: new Date().toISOString()
      };
      
      expect(() => validateSchema(schemas.OcrJobResponse, validResponse)).not.toThrow();
    });
  });
  
  describe('Schema Validation Utilities', () => {
    test('should validate correct data', () => {
      const validHealthData = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        services: {
          database: 'connected'
        }
      };
      
      expect(() => validateSchema(schemas.HealthResponse, validHealthData)).not.toThrow();
    });
    
    test('should reject invalid data', () => {
      const invalidHealthData = {
        status: 'invalid-status', // Invalid enum value
        timestamp: 'not-a-datetime',
        version: 123, // Should be string
        services: {
          database: 'maybe-connected' // Invalid enum value
        }
      };
      
      expect(() => validateSchema(schemas.HealthResponse, invalidHealthData)).toThrow();
    });
    
    test('should handle missing required fields', () => {
      const incompleteData = {
        status: 'healthy'
        // Missing required fields: timestamp, version, services
      };
      
      expect(() => validateSchema(schemas.HealthResponse, incompleteData)).toThrow();
    });
  });
  
  describe('Type Safety Validation', () => {
    test('should ensure TypeScript types match runtime validation', () => {
      // This test ensures that TypeScript compilation catches type mismatches
      const healthResponse: HealthResponse = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        services: {
          database: 'connected'
        }
      };
      
      // This should compile without errors and validate at runtime
      expect(() => validateSchema(schemas.HealthResponse, healthResponse)).not.toThrow();
    });
  });
});
