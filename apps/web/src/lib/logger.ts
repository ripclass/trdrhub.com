/**
 * Centralized Logger Utility
 * 
 * Replaces scattered console.log statements with environment-aware logging.
 * - In production: Only errors and warnings are logged
 * - In development: All levels are logged with prefixes
 * 
 * Usage:
 * import { logger } from '@/lib/logger';
 * logger.debug('Debug info', data);
 * logger.info('Info message');
 * logger.warn('Warning');
 * logger.error('Error', error);
 */

const isDev = import.meta.env.DEV;
const isTest = import.meta.env.MODE === 'test';

// Disable all logging in tests unless explicitly enabled
const ENABLE_TEST_LOGS = false;

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  prefix?: string;
  enabledLevels?: LogLevel[];
}

const defaultConfig: LoggerConfig = {
  prefix: '[TRDR]',
  enabledLevels: isDev ? ['debug', 'info', 'warn', 'error'] : ['warn', 'error'],
};

function shouldLog(level: LogLevel, config: LoggerConfig = defaultConfig): boolean {
  if (isTest && !ENABLE_TEST_LOGS) return false;
  return config.enabledLevels?.includes(level) ?? false;
}

function formatArgs(prefix: string, level: LogLevel, args: any[]): any[] {
  const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
  return [`${prefix}[${level.toUpperCase()}][${timestamp}]`, ...args];
}

export const logger = {
  /**
   * Debug level - only shown in development
   * Use for detailed debugging information
   */
  debug: (...args: any[]) => {
    if (shouldLog('debug')) {
      console.log(...formatArgs(defaultConfig.prefix!, 'debug', args));
    }
  },

  /**
   * Info level - only shown in development
   * Use for general information about app flow
   */
  info: (...args: any[]) => {
    if (shouldLog('info')) {
      console.info(...formatArgs(defaultConfig.prefix!, 'info', args));
    }
  },

  /**
   * Warn level - shown in all environments
   * Use for potential issues that don't break functionality
   */
  warn: (...args: any[]) => {
    if (shouldLog('warn')) {
      console.warn(...formatArgs(defaultConfig.prefix!, 'warn', args));
    }
  },

  /**
   * Error level - shown in all environments
   * Use for errors that affect functionality
   */
  error: (...args: any[]) => {
    if (shouldLog('error')) {
      console.error(...formatArgs(defaultConfig.prefix!, 'error', args));
    }
  },

  /**
   * Create a namespaced logger for a specific module
   */
  createLogger: (namespace: string): typeof logger => ({
    debug: (...args: any[]) => {
      if (shouldLog('debug')) {
        console.log(...formatArgs(`[${namespace}]`, 'debug', args));
      }
    },
    info: (...args: any[]) => {
      if (shouldLog('info')) {
        console.info(...formatArgs(`[${namespace}]`, 'info', args));
      }
    },
    warn: (...args: any[]) => {
      if (shouldLog('warn')) {
        console.warn(...formatArgs(`[${namespace}]`, 'warn', args));
      }
    },
    error: (...args: any[]) => {
      if (shouldLog('error')) {
        console.error(...formatArgs(`[${namespace}]`, 'error', args));
      }
    },
    createLogger: logger.createLogger,
  }),
};

// Export a no-op logger for production builds where logging should be completely disabled
export const silentLogger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
  createLogger: () => silentLogger,
};

export default logger;
