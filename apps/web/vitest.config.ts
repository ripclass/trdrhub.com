import path from 'path';
import { mergeConfig, defineConfig } from 'vitest/config';
import baseConfig from './vite.config';

export default mergeConfig(
  baseConfig,
  defineConfig({
    root: __dirname,
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@shared/types': path.resolve(__dirname, '../../packages/shared-types/src'),
      },
      include: ['src/**/*.{test,spec}.{ts,tsx}', 'src/**/__tests__/**/*.{test,spec}.{ts,tsx}'],
      exclude: ['tests/**', 'node_modules/**'],
    },
  }),
);
