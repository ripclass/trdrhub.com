import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@shared/types': path.resolve(__dirname, '../../packages/shared-types/src'),
    },
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json'],
  },
  server: {
    port: 3000,
    host: true,
  },
  build: {
    sourcemap: true,
    // Ensure clean build output directory on each build
    emptyOutDir: true,
    // Use content-hash only (no timestamp) so index.html and asset filenames
    // stay consistent within a single build. The hash changes whenever the
    // content changes, providing natural cache-busting without the risk of
    // mismatched filenames between index.html and /assets/*.
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@shared/types': path.resolve(__dirname, '../../packages/shared-types/src'),
    },
    css: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}', 'src/**/__tests__/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['tests/**', 'node_modules/**'],
  },
})
