import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logger } from '@/lib/logger';

describe('logger utility', () => {
  describe('interface', () => {
    it('has debug, info, warn, error methods', () => {
      expect(typeof logger.debug).toBe('function');
      expect(typeof logger.info).toBe('function');
      expect(typeof logger.warn).toBe('function');
      expect(typeof logger.error).toBe('function');
    });

    it('has createLogger method', () => {
      expect(typeof logger.createLogger).toBe('function');
    });

    it('methods are callable without errors', () => {
      // These should not throw, regardless of environment
      expect(() => logger.debug('test')).not.toThrow();
      expect(() => logger.info('test')).not.toThrow();
      expect(() => logger.warn('test')).not.toThrow();
      expect(() => logger.error('test')).not.toThrow();
    });
  });

  describe('createLogger', () => {
    it('creates a namespaced logger', () => {
      const authLogger = logger.createLogger('Auth');
      expect(typeof authLogger.debug).toBe('function');
      expect(typeof authLogger.error).toBe('function');
    });

    it('can create nested loggers', () => {
      const authLogger = logger.createLogger('Auth');
      const sessionLogger = authLogger.createLogger('Session');
      expect(typeof sessionLogger.debug).toBe('function');
    });

    it('namespaced loggers are callable', () => {
      const testLogger = logger.createLogger('Test');
      expect(() => testLogger.debug('test message', { data: 1 })).not.toThrow();
      expect(() => testLogger.error('error message', new Error('test'))).not.toThrow();
    });
  });

  describe('arguments', () => {
    it('accepts multiple arguments', () => {
      expect(() => logger.debug('Message', { data: 1 }, 'extra')).not.toThrow();
    });

    it('accepts Error objects', () => {
      const error = new Error('Test error');
      expect(() => logger.error('Failed:', error)).not.toThrow();
    });

    it('accepts no arguments', () => {
      expect(() => logger.debug()).not.toThrow();
    });
  });
});

